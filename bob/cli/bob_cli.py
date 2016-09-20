import argparse
from bob.common import db
from bob.common import queues
from bob.common.entities import Task


def _list_tasks():
    for task in db.load_all_tasks():
        print ('{0}:{1} {2}  {3}  {4}'.format(task.git_repo,
                                        task.git_branch,
                                        task.git_tag,
                                        task.status,
                                        task.modified_at))


def cmd_list(args):
    _list_tasks()


def cmd_ps(args):
    for task in db.tasks_ps():
        print (task)


def _build(repo, branch='master', tag=None):
    task = Task(git_repo=repo, git_branch=branch, git_tag=tag)
    db.save_task(task)
    queues.enqueue_task(task)
    print('done')


def cmd_build(args):
    if len(args) == 1:
        _build(args[0])
    elif len(args) == 2:
        _build(args[0], args[1])
    elif len(args) == 3:
        _build(args[0], args[1], args[2])


parser = argparse.ArgumentParser()
parser.add_argument('cmd', action='store', help='ls, ps, build')
parser.add_argument('args', action='store', nargs='*')
args = parser.parse_args()

if args.cmd == 'ls':
    cmd_list(args.args)

if args.cmd == 'ps':
    cmd_ps(args.args)

if args.cmd == 'build':
    cmd_build(args.args)

