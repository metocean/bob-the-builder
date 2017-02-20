import yaml
import os
from shutil import rmtree
import json

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


def _get_image_matching_log(build_path):
    return os.path.join(build_path, 'image-matching.log')


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


def _write_log_to_db(text, log_path, task):
    if not text or len(text) == 0:
        return
    if task is None:
        return
    task.save_log(text, log_path)
    db.save_task(task)


def _write_log_file_and_db(text, log_path, task):
    if not text or len(text) == 0:
        return
    if task is None:
        return
    with open(log_path, 'w') as f:
        f.write(text)
    task.save_log(text, log_path)
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
                         tail_callback=_write_log_to_db,
                         tail_callback_obj=task)


def do_test_dockers(task, build_path, source_path, docker_compose_file, service_to_test):
    print('do_test_dockers')
    os.chdir(source_path)

    execute_with_logging('docker-compose -f {0} run {1}'.format(docker_compose_file, service_to_test),
                         log_filename=_get_test_log(build_path),
                         tail_callback=_write_log_to_db,
                         tail_callback_obj=task)


def _map_services_to_images(source_path, services_to_push, local_images):
    """
    :param source_path: the source directory path to where the docker-compose.yml lives.
    :param services_to_push: a dictionary of docker_compose services mapping the docker hub push image name.
    :return: a dictionary of local image names to docker hub image names.
    """
    src_dirname = base_dirname(source_path)
    images = {}
    for image in local_images:
        for repo_tag_name in image['RepoTags']:
            # if service name is used in bob-the-build.yml
            if repo_tag_name.startswith(src_dirname):
                for service_name in services_to_push:
                    docker_hub_name = services_to_push[service_name]
                    if ':' in repo_tag_name:
                        repo_tag_name = repo_tag_name.split(':', 1)[0]
                    if repo_tag_name.endswith(service_name):
                        images[docker_hub_name] = image['Id']

            # else image name is used in bob-the-build.yml
            else:
                for image_name in services_to_push:
                    docker_hub_name = services_to_push[image_name]
                    if ':' not in image_name:
                        image_name += ':latest'
                    if repo_tag_name == image_name:
                        images[docker_hub_name] = image['Id']
    return images


def do_push_dockers(task, build_path, source_path, services_to_push):
    print('do_push_dockers')

    local_images = []
    for image in get_recent_images():
        local_images.append({'Id': image['Id'], 'RepoTags': image['RepoTags']})
    images_to_push = _map_services_to_images(source_path, services_to_push, local_images)

    msg = 'local images found:\n{0}'.format(json.dumps(local_images, indent=2))
    msg += '\n\nimages match for push:\n{0}'.format(json.dumps(images_to_push, indent=2))
    print(msg)
    _write_log_file_and_db(msg, _get_image_matching_log(build_path), task)

    if not images_to_push and len(images_to_push) == 0:
        raise BobTheBuilderException(
            'Could not match any images to push to docker hub:\r\n{0}'.format(services_to_push))

    settings = load_settings()

    if 'docker_hub' in settings and 'login' in settings['docker_hub'] and 'password' in settings['docker_hub']:
        execute('docker login -u {login} -p {password}'.format(login=settings['docker_hub']['login'],
                                                               password=settings['docker_hub']['password']))

    if task.git_tag and len(task.git_tag) and task.git_tag != 'latest':
        tag = task.git_tag
    else:
        tag = task.git_branch

    if tag == 'master':
        tag = 'latest'

    for docker_hub_image in images_to_push:
        local_image_name = images_to_push[docker_hub_image]
        docker_hub_tag = tag

        #dirty dirty prefix hack for Tom.D!
        if ':' in docker_hub_image:
            if docker_hub_tag == 'latest' or not docker_hub_tag or len(docker_hub_tag) == 0:
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
            tail_callback=_write_log_to_db,
            tail_callback_obj=task)

        execute_with_logging(
                'docker push {0}:{1}'.format(docker_hub_image, docker_hub_tag),
                log_filename=_get_push_log(build_path),
                tail_callback=_write_log_to_db,
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
                tail_callback=_write_log_to_db,
                tail_callback_obj=task)
        except:
            pass

    rmtree(source_path)
