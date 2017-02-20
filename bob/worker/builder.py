import yaml
import os
from shutil import rmtree

from bob.common.exceptions import BobTheBuilderException
from bob.worker.settings import load_settings
from bob.worker.docker_client import get_recent_images
from bob.worker.git_hub import download_tag_source, download_branch_source
from bob.worker.tools import (execute,
                              execute_with_logging,
                              rename_basedir,
                              base_dirname)
import bob.common.db as db


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


def _save_log_to_task(text, log_path, task):
    if not text or len(text) == 0:
        return
    if task is None:
        return
    task.save_log(text, log_path, insert_first=True)
    db.save_task(task)


def do_download_git_repo(task, build_path, created_at_str):
    print('do_download_git_repo')

    settings = load_settings()

    if task.git_tag and task.git_tag != 'latest':
        source_path = download_tag_source(task.git_repo,
                                          task.git_tag,
                                          build_path,
                                          settings['git_hub']['login'],
                                          settings['git_hub']['password'])
    else:
        source_path = download_branch_source(task.git_repo,
                                             build_path,
                                             task.git_branch,
                                             settings['git_hub']['login'],
                                             settings['git_hub']['password'])

    with open(os.path.join(source_path, 'bob-the-builder.yml'), 'r') as f:
        build = yaml.load(f)

        if not ('docker_compose' in build):
            raise BobTheBuilderException('Invalid "bob-the-builder.yml" file, could not find "docker_compose" att')

        if not ('services_to_push' in build['docker_compose']):
            raise BobTheBuilderException('Invalid "bob-the-builder.yml" file, could not find "services_to_push" att')

        docker_compose_file = build['docker_compose'].get('file', 'docker-compose.yml')
        services_to_push = build['docker_compose']['services_to_push']
        test_service = build['docker_compose'].get('test_service')
        notification_emails = build.get('notification_emails', [])

    return (rename_basedir(source_path, created_at_str),
            docker_compose_file,
            services_to_push,
            test_service,
            notification_emails)


def do_build_dockers(task, build_path, source_path, docker_compose_file):
    print('do_build_dockers')
    os.chdir(source_path)

    if len(task.build_args) == 0:
        cmd = 'docker-compose -f {0} build '.format(docker_compose_file)
    else:
        cmd = 'docker-compose -f {0} build '.format(docker_compose_file) + ' '.join(task.build_args)

    execute_with_logging(cmd,
                         log_filename=_get_build_log(build_path),
                         tail_callback=_save_log_to_task,
                         tail_callback_obj=task)


def do_test_dockers(task, build_path, source_path, docker_compose_file, service_to_test):
    print('do_test_dockers')
    os.chdir(source_path)

    execute_with_logging('docker-compose -f {0} run {1}'.format(docker_compose_file, service_to_test),
                         log_filename=_get_test_log(build_path),
                         tail_callback=_save_log_to_task,
                         tail_callback_obj=task)


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
                    repo_tag = repo_tag_name
                    if ':' in repo_tag_name:
                        repo_tag_name = repo_tag_name.split(':', 1)[0]
                    if repo_tag_name.endswith(service_name):
                        images[repo_tag] = services_to_push[service_name]
                break
    return images


def do_push_dockers(task, build_path, source_path, services_to_push):
    print('do_push_dockers')

    images_to_push = _map_services_to_images(source_path, services_to_push)
    if not images_to_push and len(images_to_push) == 0:
        raise BobTheBuilderException('Could not match any images to push to github:\r\n{0}',
                                     services_to_push)

    settings = load_settings()

    if 'docker_hub' in settings and 'login' in settings['docker_hub'] and 'password' in settings['docker_hub']:
        execute('docker login -u {login} -p {password}'.format(login=settings['docker_hub']['login'],
                                                               password=settings['docker_hub']['password']))

    if task.git_tag and len(task.git_tag) and task.git_tag != 'latest':
        docker_hub_tag = task.git_tag
    else:
        docker_hub_tag = task.git_branch

    if docker_hub_tag == 'master':
        docker_hub_tag = 'latest'

    for local_image_name, docker_hub_image in images_to_push.items():

        #dirty dirty prefix hack for Tom.D!
        if ':' in docker_hub_image:
            if docker_hub_tag == 'latest':
                value = docker_hub_image
            else:
                value = docker_hub_image + '-' + docker_hub_tag
            value = value.split(':', 1)
            docker_hub_image = value[0]
            docker_hub_tag = value[1]

        print('pushing docker image: {0} {1}:{2}'.format(local_image_name, docker_hub_image, docker_hub_tag))

        execute_with_logging(
            'docker tag {0} {1}:{2}'.format(local_image_name, docker_hub_image, docker_hub_tag),
            log_filename=_get_tag_log(build_path),
            tail_callback=_save_log_to_task,
            tail_callback_obj=task)

        execute_with_logging(
                'docker push {0}:{1}'.format(docker_hub_image, docker_hub_tag),
                log_filename=_get_push_log(build_path),
                tail_callback=_save_log_to_task,
                tail_callback_obj=task)


def do_clean_up(task, source_path, build_path, docker_compose_file):
    print('do_clean_up')
    if not source_path or not os.path.exists(source_path):
        return

    os.chdir(source_path)
    if docker_compose_file:
        try:
            execute_with_logging(
                'docker-compose -f {0} down --remove-orphans --volumes --rmi local'.format(
                    docker_compose_file),
                log_filename=_get_down_log(build_path),
                tail_callback=_save_log_to_task,
                tail_callback_obj=task)
        except:
            pass

    rmtree(source_path)
