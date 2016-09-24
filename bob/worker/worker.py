import json
import os
import signal
from datetime import datetime
from multiprocessing import Process
from time import sleep

from bob.common.task import (State, Task)

import bob.common.queues as queues
import bob.common.db as db
from bob.worker.tools import (send_email,
                              get_ipaddress,
                              get_hostname)

from bob.worker.builder import (do_download_git_repo,
                                do_build_dockers,
                                do_test_dockers,
                                do_push_dockers,
                                do_clean_up)

from bob.worker.docker_client import (remove_all_docker_networks,
                                      remove_all_docker_images)


def _set_state(task,
               state,
               message=None,
               email_addresses=[]):

    now = datetime.utcnow()

    event = {'new_state': state,
             'old_state': task.status,
             'created_at': now.isoformat(),
             'time_diff': str(now - task.modified_at)}

    if message:
        event['new_state_message'] = message

    task.status = state
    task.status_message = message
    task.events.append(event)

    db.save_task(task)
    _send_state_email(task, state, message, email_addresses)
    return db.reload_task(task)


def _send_state_email(task, state, message, email_addresses):

    if not (email_addresses
           and len(email_addresses) > 0
           and state in (State.canceled, State.successful, State.failed)):
        return

    try:
        subject = 'build {0} {1} {2} is {3}'.format(
               task.git_repo,
               task.git_branch,
               task.git_tag,
               state,
               message)

        send_email(email_addresses,
                   subject,
                   body=subject + '\r\n{0}'.format(message))

    except Exception as ex:
        print('{0}'.format(ex))


def _run_build(git_repo, git_branch, git_tag, created_at):

    task = db.load_task(git_repo, git_branch, git_tag, created_at)
    task.builder_ipaddress = get_ipaddress()
    task.builder_hostname = get_hostname()

    build_path = None
    source_path = None
    docker_compose_file = None
    notification_emails = None
    try:
        while (task.status != State.failed
              and task.status != State.successful):

            if task.status == State.pending:
                task = _set_state(task, State.downloading)

            elif task.status == State.downloading:
                (build_path,
                 source_path,
                 docker_compose_file,
                 services_to_push,
                 test_service,
                 notification_emails) = do_download_git_repo(task)

                task = _set_state(task, State.building, email_addresses=notification_emails)

            elif task.status == State.building:
                do_build_dockers(task, build_path, source_path, docker_compose_file)
                if test_service:
                    task = _set_state(task, State.testing, email_addresses=notification_emails)
                else:
                    task = _set_state(task, State.pushing, email_addresses=notification_emails)

            elif task.status == State.testing:
                do_test_dockers(task, build_path, source_path, docker_compose_file, test_service)
                task = _set_state(task, State.pushing, email_addresses=notification_emails)

            elif task.status == State.pushing:
                do_push_dockers(task, build_path, source_path, services_to_push)
                task = _set_state(task, State.successful, email_addresses=notification_emails)

            else:
                task = _set_state(task,
                                  State.failed,
                                  'unknown state {0}'.format(task.status),
                                  email_addresses=notification_emails)

    except KeyboardInterrupt as ex:
        _set_state(task,
                   state=State.canceled,
                   message='build was canceled while {0}'.format(task.status),
                   email_addresses=notification_emails)

    except Exception as ex:
        if (task.status != State.successful
           and task.status != State.failed
           and task.status != State.canceled):
            _set_state(task,
                       state=State.failed,
                       message='build failed while {0} with error: {1}'.format(task.status, ex),
                       email_addresses=notification_emails)
        raise ex

    finally:
        do_clean_up(task, source_path, build_path, docker_compose_file)


def _stop_process(process):
    """
    stops a given process.
    Sends a SIG_INT and waits for 8 seconds, then send a SIG_KILL if it did not exit.
    """
    if not process or not process.is_alive():
        return

    print('terminating pid:{0}'.format(process.pid))
    process.terminate()
    counter = 8
    while process.is_alive() and counter:
        counter -= 1
        sleep(1)

    if not counter:
        print('killing pid:{0} it did not terminate timely like'.format(process.pid))
        os.kill(process.pid, signal.SIGKILL)


def _cancel_task(task, process):
    if (task.status != State.successful
           and task.status != State.failed
           and task.status != State.canceled):
        _stop_process(process)
        _set_state(task, State.canceled, 'task was canceled')


def main():
    db.create_task_table()
    queues._create_task_queue()

    print('removing all docker networks')
    remove_all_docker_networks()
    print('removing all docker images')
    remove_all_docker_images()

    task_queue = queues.get_task_queue()

    while task_queue:

        messages = task_queue.receive_messages(MaxNumberOfMessages=1, WaitTimeSeconds=1)
        if not messages or len(messages) == 0:
            continue

        task = Task.from_json(messages[0].body)
        if not task:
            continue

        # clean up old dockers sitting here before.
        remove_all_docker_networks()
        remove_all_docker_images()

        process = Process(target=_run_build, args=(
            task.git_repo,
            task.git_branch,
            task.git_tag,
            task.created_at,))

        try:
            process.start()

            # delete message for queue now we are actually processing it.
            messages[0].delete()

            while process.is_alive():
                process.join(2)

                if process.is_alive():
                    task = db.reload_task(task)
                    if task.status == State.cancel:
                        _cancel_task(task, process)

        except KeyboardInterrupt:
            pass

        if process and process.is_alive():
            _cancel_task(db.reload_task(task), process)

        remove_all_docker_networks()
        remove_all_docker_images()


if __name__ == "__main__":
    main()
