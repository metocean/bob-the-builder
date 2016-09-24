#!/usr/bin/env python3

import os
import pwd
import argparse
from bob.common import db
from bob.common import queues
from bob.common.task import Task


def _print_task(task, format_str):
    print(format_str.format(repo=task.git_repo,
                            branch=task.git_branch,
                            tag=task.git_tag,
                            status=task.status,
                            modified_at=task.modified_at,
                            created_at=task.created_at,
                            created_by=task.get_created_by(),
                            builder_hostname=task.get_builder_hostname(),
                            builder_ipaddress=task.get_builder_ipaddress(),
                            run_time=task.run_time()))


def cmd_list(args):
    format_str = '{status} - {repo} - {branch} - {tag} - {run_time} - {builder_hostname} - {created_by}'
    print(format_str)
    for task in db.load_all_tasks():
        _print_task(task, format_str)


def cmd_ps(args):
    format_str = '{status} - {repo} - {branch} - {tag} - {run_time} - {builder_hostname} - {created_by}'
    print(format_str)
    for task in db.tasks_ps():
        _print_task(task, format_str)


def _get_username():
    try:
        return pwd.getpwuid(os.getuid())[0]
    except:
        return 'cli'


def _build(repo, branch='master', tag=None):
    task = Task(git_repo=repo,
                git_branch=branch,
                git_tag=tag,
                created_by=_get_username())
    db.save_task(task)
    queues.enqueue_task(task)
    print('ok')

_build('metocean/gregc')
def cmd_build(args):
    if len(args) == 1:
        _build(args[0])
    elif len(args) == 2:
        _build(args[0], args[1])
    elif len(args) == 3:
        _build(args[0], args[1], args[2])


def cmd_cancel(args):
    print('TODO')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', action='store', help='build, cancel, ls, ps')
    parser.add_argument('args', action='store', nargs='*')
    args = parser.parse_args()

    if args.cmd == 'ls' or args.cmd == 'list':
        cmd_list(args.args)

    if args.cmd == 'ps':
        cmd_ps(args.args)

    if args.cmd == 'build':
        cmd_build(args.args)

    if args.cmd == 'cancel':
        cmd_cancel(args.args)


if __name__ == 'main':
    main()
