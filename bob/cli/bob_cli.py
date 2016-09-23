#!/usr/bin/env python3

import argparse
from bob.common import db
from bob.common import queues
from bob.common.task import Task


def cmd_list(args):
    format_str = '{status} - {repo} - {branch} - {tag} - {modified_at} - {builder_hostname}'
    print(format_str)
    for task in db.load_all_tasks():
        print (format_str.format(repo=task.git_repo,
                                 branch=task.git_branch,
                                 tag=task.git_tag,
                                 status=task.status,
                                 modified_at=task.modified_at,
                                 builder_hostname=task.get_builder_hostname()))


def cmd_ps(args):
    format_str = '{status} - {repo} - {branch} - {tag} - {modified_at} - {builder_hostname}'
    print(format_str)
    for task in db.tasks_ps():
        print (format_str.format(repo=task.git_repo,
                                 branch=task.git_branch,
                                 tag=task.git_tag,
                                 status=task.status,
                                 modified_at=task.modified_at,
                                 builder_hostname=task.get_builder_hostname()))


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


def cmd_cancel(args):
    print( 'TODO' )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cmd', action='store', help='ls, ps, build')
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
main()

if __name__ == 'main':
    main()
