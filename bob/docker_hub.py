from bob.tools import execute
import os


def push(tag_name, build_log, output_path, repo_settings):

    if not ('docker_compose' in repo_settings and 'services' in repo_settings['docker_compose']):
        return

    built = {}
    with open(build_log, 'r') as log:
        build_name = None
        for line in log.readlines():
            if not build_name:
                if line.startswith('Building '):
                    build_name = line.replace('Building ', '').rstrip('\n')
            else:
                if line.startswith('Successfully built '):
                    built[build_name] = line.replace('Successfully built ', '').rstrip('\n')
                    build_name = None

    if len(built) == 0:
        return

    for service_name in repo_settings['docker_compose']['services']:

        if not (service_name in built):
            continue
        docker_hub_image = repo_settings['docker_compose']['services'][service_name]['docker_hub_image']
        image_id = built[service_name]

        if not tag_name:
            tag_name = 'latest'

        print 'pushing docker image: {0} {1}:{2}'.format(image_id, docker_hub_image, tag_name)

        execute('docker tag {0} {1}:{2}'.format(image_id, docker_hub_image, tag_name),
                os.path.join(output_path, 'docker-tag.log'))

        execute('docker push {0}:{1}'.format(docker_hub_image, tag_name),
                os.path.join(output_path, 'docker-push.log'))
