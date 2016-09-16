import argparse
from bob.common import db
from bob.common import queues
from bob.common.entities import Task


def _list_builds():
    for build in db.db_load_all_builds():
        print ('{0}:{1}'.format(build.git_repo, build.git_branch))
        print (' notify: ' + ','.join(build.notification_emails))
        print (' docker-compose-file: {0}'.format(build.docker_compose.get('docker_compose_file')))
        print (' test-service: {0}'.format(build.docker_compose.get('test_service')))
        print (' services to push:')
        services_to_push = build.docker_compose.get('services_to_push')
        if services_to_push:
            for name in services_to_push:
                print ('  {0} -> {1}'.format(name, services_to_push[name]))
        print ('')


def _list_tasks():
    for task in db.db_load_all_tasks():
        print ('{0}:{1} {2}  {3}  {4}'.format(task.git_repo,
                                        task.git_branch,
                                        task.git_tag,
                                        task.status,
                                        task.modified_at))


def cmd_list(args):
    if len(args) == 1:
        if args[0] in ('task' or 'tasks'):
            _list_tasks()
        _list_builds()

    elif len(args) == 2:
        if args[0] in ('task' or 'tasks'):
            _list_tasks()
        _list_builds()


def cmd_ps(args):
    for task in db.db_tasks_ps():
        print (task)


def _build(repo, branch=None):
    if not branch:
        branch = 'master'

    build = db.db_load_build(repo, branch)
    if not build:
        print 'build does not exits, please use "add" cmd to make a new build'
        return

    task = Task(git_repo=repo, git_branch=branch)
    db.db_save_task(task)
    queues.enqueue_task(task)
    print 'done'


def cmd_build(args):
    if len(args) == 1:
        _build(args[0])
    if len(args) == 2:
        _build(args[0], args[1])


def cmd_cancel(args):
    print('NOT IMPED cancel {0}'.format(args))


def cmd_add(args):
    print('NOT IMPED add {0}'.format(args))


def cmd_del(args):
    print('NOT IMPED del {0}'.format(args))


parser = argparse.ArgumentParser()
parser.add_argument('cmd', action='store', help='ls, ps, build, cancel, add, del')
parser.add_argument('args', action='store', nargs='*')
args = parser.parse_args()

if args.cmd == 'ls':
    cmd_list(args.args)

if args.cmd == 'ps':
    cmd_ps(args.args)

if args.cmd == 'build':
    cmd_build(args.args)

if args.cmd == 'add':
    cmd_add(args.args)

if args.cmd == 'del':
    cmd_del(args.args)
