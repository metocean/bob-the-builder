#!/usr/bin/env python3

import os
import pwd
import argparse
from bob.common import db
from bob.common import queues
from bob.common.task import Task
from subprocess import check_output


def _get_repo():
    """
    finds the git repo name if the user's current directory is a git repo
    """
    try:
        output = check_output('git config --get remote.origin.url', shell=True)
        if not output:
            return None
        output = output.decode("utf-8").strip().replace('\r\n', '').replace('\n', '')
        repo = output
        if 'git@' in repo:
            repo = repo[repo.find(':')+1:]
        elif repo.startswith('https://'):
            repo = repo.replace('https://', '')
            if '/' not in repo:
                return None
            repo = repo[repo.find('/')+1:]
        else:
            raise NotImplementedError('cannot understand repo: {0}'.format(output))
        if repo.endswith('.git'):
            repo = repo[0:repo.rindex('.git')]
        return repo.lower()
    except Exception:
        return None


def _get_branch(default='master'):
    """
    finds the git repo name if the user's current directory is a git repo
    """
    try:
        output = check_output('git rev-parse --abbrev-ref HEAD', shell=True)
        if not output:
            return default
        return output.decode("utf-8").strip()
    except Exception:
        return default


def _print_task(task, format_str):
    print(format_str.format(repo=task.git_repo,
                            branch=task.git_branch,
                            tag=task.git_tag,
                            state=task.state,
                            modified_at=task.modified_at,
                            created_at=task.created_at,
                            created_by=task.get_created_by(),
                            builder_hostname=task.get_builder_hostname(),
                            builder_ipaddress=task.get_builder_ipaddress(),
                            duration=task.get_duration()))


def cmd_list(args):
    format_str = '{state} - {repo} - {branch} - {tag} - {duration} - {builder_hostname} - {created_by}'
    print(format_str)
    for task in db.load_all_tasks():
        _print_task(task, format_str)


def cmd_ps(args):
    format_str = '{state} - {repo} - {branch} - {tag} - {duration} - {builder_hostname} - {created_by}'
    print(format_str)
    for task in db.tasks_ps():
        _print_task(task, format_str)


def _get_username():
    try:
        return pwd.getpwuid(os.getuid())[0]
    except:
        return 'cli'


def _build(repo=_get_repo(), branch=_get_branch('master'), tag=None):
    if not repo:
        print('failed: are you in a git repo?')
        return

    task = Task(git_repo=repo,
                git_branch=branch,
                git_tag=tag,
                created_by=_get_username())
    db.save_task(task)
    queues.enqueue_task(task)

    msg = 'ok - building: ' + repo
    if branch:
        msg += ' - ' + branch
    if tag:
        msg += ' - ' + tag
    print(msg)


def cmd_build(args):
    if len(args) == 0:
        _build()
    elif len(args) == 1:
        _build(args[0])
    elif len(args) == 2:
        _build(args[0], args[1])
    elif len(args) == 3:
        _build(args[0], args[1], args[2])
    else:
        print('failed')


def cmd_cancel(args):
    print('Currently not implemented, please use the web interface for the time being.')


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
