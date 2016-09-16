import base64
import os
import subprocess
from datetime import datetime
from shutil import rmtree

from bob.worker.docker_client import get_recent_images
from bob.worker.git_hub import download_release_source, download_branch_source
from bob.worker.tools import base_dirname
from bob.worker.tools import mkdir_p, execute, rename_basedir


def _get_build_log(build_path):
    return os.path.join(build_path, 'docker-build.log')


def _get_tag_log(build_path):
    return os.path.join(build_path, 'docker-tag.log')


def _get_push_log(build_path):
    return os.path.join(build_path, 'docker-push.log')


def _get_test_log(build_path):
    return os.path.join(build_path, 'docker-test.log')


def _get_down_log(build_path):
    return os.path.join(build_path, 'docker-down.log')


def _get_git_tag_log(build_path):
    return os.path.join(build_path, 'git-tag.json')


def _get_git_release_log(build_path):
    return os.path.join(build_path, 'git-release.json')


def _tail_log_to_task(task, log_path, num_lines=100):
    if not os.path.isfile(log_path):
        return
    text = subprocess.check_output(['tail', log_path, '-n ' + str(num_lines)], shell=False)
    if not text or len(text) == 0:
        return
    # text = base64.b64encode(text)
    # if not text or len(text) == 0:
    #     return
    task.logs.append({'filename': os.path.basename(log_path),
                      'path:': log_path,
                      'text': text,
                      'created_at': datetime.utcnow().isoformat()})


def do_download_git_repo(task, build):
    print('do_download_git_repo')

    # note there are no spearates in the time string beacause its used for matching up
    # build image names in do_docker_push(), DONOT change this format! hackie i know :P
    created_at_str = task.created_at.strftime("%Y%m%d%H%M%S%f")

    build_path = '/tmp/bob/build/{git_repo}/{git_branch}/{git_tag}/{created_at}'.format(
        git_repo=task.git_repo,
        git_branch=task.git_branch,
        git_tag=task.git_tag,
        created_at=created_at_str)

    if os.path.exists(build_path):
        rmtree(build_path)
    mkdir_p(build_path)

    login = build.git_hub_login
    if not login or len(login) == 0:
        raise Exception('git hub login not found')

    try:
        if task.git_tag and task.git_tag != 'latest':
            source_path = download_release_source(task.git_repo,
                                                  task.git_tag,
                                                  build_path,
                                                  login['login'],
                                                  login['password'])
        else:
            source_path = download_branch_source(task.git_repo,
                                                 build_path,
                                                 task.git_branch,
                                                 login['login'],
                                                 login['password'])
    finally:
        _tail_log_to_task(task, _get_git_tag_log(build_path))
        _tail_log_to_task(task, _get_git_release_log(build_path))

    return build_path, rename_basedir(source_path, created_at_str)


def do_build_dockers(task, build, build_path, source_path):
    """
    builds the docker or run docker composes.
    """
    print('do_build_dockers')

    os.chdir(source_path)
    log_path = _get_build_log(build_path)

    try:
        execute('docker-compose -f {0} build --no-cache --pull --force-rm'.format(
            build.docker_compose['docker_compose_file']),
            log_path)
    finally:
        _tail_log_to_task(task, log_path)


def do_test_dockers(task, build, build_path, source_path):
    print('do_test_dockers')
    os.chdir(source_path)

    compose = build.docker_compose
    log_path = _get_test_log(build_path)
    try:
        execute('docker-compose -f {0} run {1}'.format(compose['docker_compose_file'],
                                                       compose['test_service']),
                log_path)
    finally:
        _tail_log_to_task(task, log_path)


def _map_services_to_images(source_path, services_to_push):
    """
    :param source_path: the source directory path to where the docker-compose.yml lives.
    :param services_to_push: a dictionary of docker_compose services mapping the docker hub push image name.
    :return: a dictionary of local image names to docker hub image names.
    """
    src_dirname = base_dirname(source_path)
    images = {}
    for image in get_recent_images():
        for repo_tag_name in image['RepoTags']:
            if repo_tag_name.startswith(src_dirname):
                for service_name in services_to_push:
                    if repo_tag_name.endswith(service_name):
                        images[repo_tag_name] = services_to_push[service_name]
                break
    return images


def do_push_dockers(task, build, build_path, source_path):
    print('do_push_dockers')

    services_to_push = build.docker_compose['services_to_push']
    images_to_push = _map_services_to_images(source_path, services_to_push)

    tag_log_path = _get_tag_log(build_path)
    push_log_path = _get_push_log(build_path)
    try:
        for local_image_name, docker_hub_image in images_to_push.items():

            print('pushing docker image: {0} {1}:{2}'.format(local_image_name, docker_hub_image, task.git_tag))

            execute('docker tag {0} {1}:{2}'.format(local_image_name, docker_hub_image, task.git_tag),
                    tag_log_path)

            execute('docker push {0}:{1}'.format(docker_hub_image, task.git_tag),
                    push_log_path)
    finally:
        _tail_log_to_task(task, tag_log_path)
        _tail_log_to_task(task, push_log_path)


def do_clean_up(task, build, source_path, build_path):
    print('do_clean_up')

    if not os.path.isdir(source_path):
        return

    os.chdir(source_path)
    if build:
        log_path = _get_down_log(build_path)
        try:
            execute('docker-compose -f {0} down --remove-orphans --volumes --rmi local'.format(
                    build.docker_compose['docker_compose_file']),
                    log_path)
        except:
            pass
        finally:
            _tail_log_to_task(task, log_path)

    rmtree(source_path)
