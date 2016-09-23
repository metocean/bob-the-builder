import docker
from time import time


def get_recent_images(docker_client=docker.Client(),
                      created_from_in_epoc=time()-48*60*60):
    """
    returns images with:
     1) a Created time greater than or equal to created_from_in_epoc.
     2) Images with something in the RepoTags.
    """
    for image in docker_client.images():

        created = image.get('Created')
        if not created or created < created_from_in_epoc:
            continue

        repo_tags = image.get('RepoTags')
        if not repo_tags or len(repo_tags) == 0:
            continue

        has_valid_tag = False
        for tag in repo_tags:
            if tag and tag != '<none>:<none>':
                has_valid_tag = True
                break

        if not has_valid_tag:
            continue

        yield image


def remove_all_docker_networks(docker_client=docker.Client()):
    """
    removes an non-default docker networks, and stops any container relate to them.
    """
    for net in docker_client.networks():
        if net['Name'] in ('bridge', 'host', 'none'):
            continue

        for con_id in net['Containers']:
            docker_client.stop(con_id)

        docker_client.remove_network(net['Id'])


def remove_all_docker_images(client=docker.Client()):
    """
    removes all images and containers on machine
    """
    for container in client.containers(all=True):
        if container.get('State') == 'running':
            print('stopping container: {0}'.format(container))
            client.stop(container)

    for container in client.containers(all=True):
        print('removing container: {0}'.format(container))
        client.remove_container(container)

    for image in client.images():
        print('removing image: {0}'.format(image))
        client.remove_image(image, force=True)


def remove_dangling_docker_images(client=docker.Client()):
    """
    removes all images and containers on machine
    """
    for container in client.containers(all=True):
        if container.get('State') == 'running':
            print('stopping container: {0}'.format(container))
            client.stop(container)

    for container in client.containers(all=True):
        print('removing container: {0}'.format(container))
        client.remove_container(container)

    for image in client.images(all=True, filters={'dangling': True}):
        print('removing image: {0}'.format(image))
        client.remove_image(image, force=True)
