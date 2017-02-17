#!/usr/bin/env python3

import os
import pwd
import sys
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
                            build_args=task.build_args,
                            state=task.state,
                            modified_at=task.modified_at,
                            created_at=task.created_at,
                            created_by=task.get_created_by(),
                            builder_info=task.get_builder_info(),
                            duration=task.get_duration()))


def cmd_list(repo, branch, tag):
    format_str = '{state} - {repo} - {branch} - {tag} - {build_args} - {duration} - {builder_info} - {created_by}'
    print(format_str)
    for task in db.tasks_list(git_repo=repo, git_branch=branch, git_tag=tag):
        _print_task(task, format_str)


def cmd_ps(repo, branch, tag):
    format_str = '{state} - {repo} - {branch} - {tag} - {build_args} - {duration} - {builder_info} - {created_by}'
    print(format_str)
    for task in db.tasks_ps(git_repo=repo, git_branch=branch, git_tag=tag):
        _print_task(task, format_str)


def _get_username():
    try:
        return pwd.getpwuid(os.getuid())[0]
    except:
        return 'cli'


def _build(repo, branch, tag, args):
    if not repo:
        print('failed: are you in a git repo?')
        return

    task = Task(git_repo=repo,
                git_branch=branch,
                git_tag=tag,
                build_args=args,
                created_by=_get_username())

    db.save_task(task)
    queues.enqueue_task(task)

    msg = 'ok - building: ' + repo
    if branch:
        msg += ' - ' + branch
    if tag:
        msg += ' - ' + tag
    print(msg)


def print_build_help():
    print ("""Usage: build [options] [SERVICE...]
Options:
    --repo      Git Repo to build, will find from current directory otherwise.
    --branch    Git Branch to build, will find from current directory otherwise.
    --tag       Git Tag to build.
    --force-rm  Always remove intermediate containers.
    --no-cache  Do not use cache when building the image.
    --pull      Always attempt to pull a newer version of the image.
""")


def main():

    if len(sys.argv) < 2:
        print ('commands are: build, ps, ls, cancel')
        sys.exit(1)

    program = sys.argv.pop(0)
    cmd = sys.argv.pop(0)

    repo = None
    branch = None
    tag = None
    args = []
    while len(sys.argv):
        arg = sys.argv.pop(0)
        if arg == '--help':
            print_build_help()
            return
        elif arg == '--repo':
            repo = sys.argv.pop()
        elif arg == '--branch':
            branch = sys.argv.pop()
        elif arg == '--tag':
            tag = sys.argv.pop()
        else:
            args.append(arg)

    if not repo:
        repo = _get_repo()

    if not branch:
        branch = _get_branch('master')

    if cmd == 'build':
        _build(repo=repo, branch=branch, tag=tag, args=args)
    elif cmd == 'ps':
        print('ps')
    elif cmd == 'ls':
        print('ls')
    elif cmd == 'cancel':
        print('cancel')


if __name__ == "__main__":
    # main()
    _build('metocean/gregc', branch='master', tag=None, args=[])
    cmd_ps(repo='metocean/gregc', branch='master', tag=None)
    cmd_list(repo='metocean/gregc', branch='master', tag=None)
