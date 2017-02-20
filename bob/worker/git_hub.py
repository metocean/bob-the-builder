import json
import os
from glob import glob

from bob.common.exceptions import BobTheBuilderException
from bob.worker.tools import url_get_json, url_download


def _check_response(status, response):
    if 'message' in response:
        raise BobTheBuilderException('github error: {0}'.format(response['message']))


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


def _download(url, file_path, login, password):

    status = url_download(url,
                         file_path,
                         login,
                         password)

    if status == 404:
        raise BobTheBuilderException('{status}: Could find download "{url}"'.format(url=url, status=status))

    if status == 401:
        raise BobTheBuilderException('{status}: Could download unauthorized "{url}"'.format(url=url, status=status))

    if status >= 400:
        raise BobTheBuilderException('{status}: Could download "{url}"'.format(url=url, status=status))


def download_tag_source(repo, tag_name, output_path, auth_username, auth_password):
    """
    downloads and unzip the source for the given git repo's release.
    :param repo_owner_name: the git repo owner.
    :param tag_name: the git release tag name e.g. 'v1.0.2'.
    :param output_path: the directory where the logs and source are to be saved.
    :param auth_username: git username / login.
    :param auth_password: git password.
    :return: the directory path to source.
    """
    status, tag = _get_tag(auth_username, auth_password, repo, tag_name)
    if not tag:
        raise BobTheBuilderException('Git tags request failed status:{0}'.format(status))

    with open(os.path.join(output_path, 'git-tag.json'), 'w') as f:
        f.write(json.dumps(tag, indent=2))

    download_url = tag.get('zipball_url')
    if not download_url:
        raise BobTheBuilderException('Could find a download url')

    release_file = os.path.join(output_path, 'src.zip')
    source_path = os.path.join(output_path, 'src')

    status = _download(download_url, release_file, auth_username, auth_password)

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

    _download('https://api.github.com/repos/{0}/{1}/{2}'.format(repo,
                                                                       'zipball',
                                                                       branch),
                        release_file,
                        login,
                        password)

    os.system('unzip {0} -d {1}'.format(release_file, source_path))

    result = glob(os.path.join(source_path, '*'))
    if len(result) == 1 and os.path.isdir(result[0]):
        source_path = result[0]

    if source_path and not source_path.endswith('/'):
        source_path += '/'

    os.remove(release_file)

    print(source_path)
    return source_path
