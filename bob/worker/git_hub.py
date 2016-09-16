import json
import os
from glob import glob

from bob.common.exceptions import BobTheBuilderException
from bob.worker.tools import url_get_json, url_download


def _check_response(status, response):
    if 'message' in response:
        raise BobTheBuilderException('github error: {0}'.format(response['message']))


def _get_release(auth_username, auth_password, repo, tag_name):

    status, releases = url_get_json('https://api.github.com/repos/{0}/releases'.format(repo),
                                    auth_username,
                                    auth_password)
    if not releases:
        raise BobTheBuilderException('github release {0}:{1} not found'.format(repo, tag_name))

    _check_response(status, releases)

    for release in releases:
        if tag_name != release.get('tag_name'):
            continue
        return status, release

    raise BobTheBuilderException('github release {0}:{1} not found'.format(repo, tag_name))


def _get_tag(auth_username, auth_password, repo, tag_name):

    status, tags = url_get_json('https://api.github.com/repos/{0}/tags'.format(repo),
                                auth_username, auth_password)
    if not tags:
        raise BobTheBuilderException('github tag {0}:{1} not found'.format(repo, tag_name))

    _check_response(status, tags)

    for tag in tags:
        if not 'name' in tag or tag_name != tag.get('name'):
            continue
        return status, tag

    raise BobTheBuilderException('github tag {0}:{1} not found'.format(repo, tag_name))


def download_branch(repo,
                    file_path,
                    branch='master',
                    archive_format='zipball',
                    login=None,
                    password=None):

    # GET /repos/:owner/:repo/:archive_format/:ref

    return url_download('https://api.github.com/repos/{0}/{1}/{2}'.format(repo,
                                                                          archive_format,
                                                                          branch),
                        file_path,
                        login,
                        password)


def download_release_source(repo, tag_name, output_path, auth_username, auth_password):
    """
    downloads and unzip the source for the given git repo's release.
    :param repo_owner_name: the git repo owner.
    :param tag_name: the git release tag name e.g. 'v1.0.2'.
    :param output_path: the directory where the logs and source are to be saved.
    :param auth_username: git username / login.
    :param auth_password: git password.
    :return: the directory path to source.
    """
    status, release = _get_release(auth_username, auth_password, repo, tag_name)
    if not release:
        raise BobTheBuilderException('Git releases request failed status:{0}'.format(status))

    with open(os.path.join(output_path, 'git-release.json'), 'w') as f:
        f.write(json.dumps(release, indent=2))

    status, tag = _get_tag(auth_username, auth_password, repo, tag_name)
    if not tag:
        raise BobTheBuilderException('Git tags request failed status:{0}'.format(status))

    with open(os.path.join(output_path, 'git-tag.json'), 'w') as f:
        f.write(json.dumps(tag, indent=2))

    download_url = release.get('zipball_url')
    if not download_url:
        download_url = tag['zipball_url']

    if not download_url:
        raise BobTheBuilderException('Could find a download url')

    release_file = os.path.join(output_path, 'src.zip')
    source_path = os.path.join(output_path, 'src')

    status = url_download(download_url, release_file, auth_username, auth_password)
    if status == 404:
        raise BobTheBuilderException('Could not download url:{0}'.format(download_url))

    os.system('unzip {0} -d {1}'.format(release_file, source_path))

    result = glob(os.path.join(source_path, '*'))
    if len(result) == 1 and os.path.isdir(result[0]):
        source_path = result[0]

    if source_path and not source_path.endswith('/'):
        source_path += '/'

    os.remove(release_file)

    print(source_path)
    return source_path


def download_branch_source(repo, output_path, branch='master', login=None, password=None):
    """
    downloads the latest source for the given branch
    :param repo: the git repo owner.
    :param output_path: the directory where the logs and source are to be saved.
    :param auth_username: git username / login.
    :param auth_password: git password.
    :return: the directory path to source.
    """

    release_file = os.path.join(output_path, 'src.zip')
    source_path = os.path.join(output_path, 'src')

    status = download_branch(repo,
                             release_file,
                             branch=branch,
                             login=login,
                             password=password)
    if status == 404:
        raise BobTheBuilderException('Could not download "{0}:{1}"'.format(repo, branch))

    os.system('unzip {0} -d {1}'.format(release_file, source_path))

    result = glob(os.path.join(source_path, '*'))
    if len(result) == 1 and os.path.isdir(result[0]):
        source_path = result[0]

    if source_path and not source_path.endswith('/'):
        source_path += '/'

    os.remove(release_file)

    print(source_path)
    return source_path
