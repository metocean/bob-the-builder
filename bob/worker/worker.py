import os
import signal
from multiprocessing import Process
from time import sleep

from bob.common.task import (State, Task)
from bob.common.exceptions import BobTheBuilderException
import bob.common.queues as queues
import bob.common.db as db
from bob.worker.tools import (send_email,
                              get_ipaddress,
                              get_hostname,
                              tail)

from bob.worker.builder import (do_download_git_repo,
                                do_build_dockers,
                                do_test_dockers,
                                do_push_dockers,
                                do_clean_up)

from bob.worker.docker_client import (remove_all_docker_networks,
                                      remove_all_docker_images)

from bob.worker.settings import get_base_build_path
from bob.common.tools import mkdir_p
from shutil import rmtree
from datetime import datetime
import traceback


def _set_state(task,
               state,
               message=None,
               email_addresses=[]):
    task.set_state(state=state, message=message)
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


def _handle_exception(task, build_path, email_addresses, ex):

    traceback.print_exc()
    ex_type = ex.__class__.__name__
    ex_str = str(ex)

    _set_state(task,
               state=State.failed,
               message='build failed while {0} with error: {1}: {2}'.format(task.state, ex_type, ex_str),
               email_addresses=email_addresses)

    log_path = os.path.join(build_path, 'error.log')
    with open(log_path, 'w') as f:
        f.write(datetime.utcnow().isoformat() + '\n')
        traceback.print_exc(file=f)

    text = tail(filename=log_path)
    if text and len(text) > 0:
        task.save_log(text, log_path, insert_first=True)
        db.save_task(task)


def _run_build(git_repo, git_branch, git_tag, created_at):

    task = db.load_task(git_repo, git_branch, git_tag, created_at)
    task.builder_ipaddress = get_ipaddress()
    task.builder_hostname = get_hostname()

    # note there are no spearates in the time string beacause its used for matching up
    # build image names in do_docker_push(), DONOT change this format! hackie i know :P
    created_at_str = task.created_at.strftime("%Y%m%d%H%M%S%f")

    build_path = '{base_build_path}/{git_repo}/{git_branch}/{git_tag}/{created_at}'.format(
        base_build_path=get_base_build_path(),
        git_repo=task.git_repo,
        git_branch=task.git_branch,
        git_tag=task.git_tag,
        created_at=created_at_str)

    if os.path.exists(build_path):
        rmtree(build_path)
    mkdir_p(build_path)

    source_path = None
    docker_compose_file = None
    notification_emails = None
    try:
        while (task.state != State.failed
              and task.state != State.successful):

            if task.state == State.pending:
                task = _set_state(task, State.downloading)

            elif task.state == State.downloading:
                (source_path,
                 docker_compose_file,
                 services_to_push,
                 test_service,
                 notification_emails) = do_download_git_repo(task, build_path, created_at_str)

                task = _set_state(task, State.building, email_addresses=notification_emails)

            elif task.state == State.building:
                do_build_dockers(task, build_path, source_path, docker_compose_file)
                if test_service:
                    task = _set_state(task, State.testing, email_addresses=notification_emails)
                else:
                    task = _set_state(task, State.pushing, email_addresses=notification_emails)

            elif task.state == State.testing:
                do_test_dockers(task, build_path, source_path, docker_compose_file, test_service)
                task = _set_state(task, State.pushing, email_addresses=notification_emails)

            elif task.state == State.pushing:
                do_push_dockers(task, build_path, source_path, services_to_push)
                task = _set_state(task, State.successful, email_addresses=notification_emails)

            else:
                task = _set_state(task,
                                  State.failed,
                                  'unknown state {0}'.format(task.state),
                                  email_addresses=notification_emails)

    except KeyboardInterrupt as ex:
        _set_state(task,
                   state=State.canceled,
                   message='build was canceled while {0}'.format(task.state),
                   email_addresses=notification_emails)

    except Exception as ex:
        _handle_exception(task,
                          build_path=build_path,
                          email_addresses=notification_emails,
                          ex=ex)

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

    print('process pid:{0} {1}'.format(process.pid, 'failed to stop' if process.is_alive() else 'has stopped'))


def _cancel_task(task, process):
    if (task.state != State.successful
           and task.state != State.failed
           and task.state != State.canceled):
        _stop_process(process)
        _set_state(task, State.canceled, 'task was canceled')


def run():
    db.create_task_table()
    queues.create_task_queue()

    print('removing all docker networks')
    remove_all_docker_networks()
    print('removing all docker images')
    remove_all_docker_images()

    task_queue = queues.get_task_queue()

    terminate = False
    while not terminate:

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
                    if task.state == State.cancel:
                        _cancel_task(task, process)

        except KeyboardInterrupt:
            terminate = True

        if process and process.is_alive():
            _cancel_task(db.reload_task(task), process)

        remove_all_docker_networks()
        remove_all_docker_images()


def main():
    try:
        run()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
