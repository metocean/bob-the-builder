import os
import yaml
from bob.exceptions import BobTheBuilderException
from bob.tools import mkdir_if_not_exist


def _load_settings_file():

    settings_file = os.environ.get("BOB_THE_BUILDER_SETTINGS", None)

    if not settings_file:
        for dir in (os.curdir,
                    os.path.expanduser("~"),
                    os.path.expanduser("~/.bob-the-builder"),
                    os.path.expanduser("~/.config/bob-the-builder"),
                    "/etc/local/bob-the-builder/",
                    "/etc/bob-the-builder/"):
            search_path = os.path.join(dir, 'settings.yml')
            if os.path.isfile(search_path):
                settings_file = search_path
                break

    if not settings_file:
        raise BobTheBuilderException('cannot find settings.yml file')

    if not os.path.isfile(settings_file):
        raise BobTheBuilderException('cannot find settings file "{0}"'.format(settings_file))

    with open(settings_file, 'r') as stream:
        return yaml.load(stream)


def get_base_directory():

    for dir in (os.path.expanduser("~/.bob-the-builder"),
                "/var/local/bob-the-builder/",
                "/var/bob-the-builder/"):
        if os.path.isdir(dir):
            return dir

    return mkdir_if_not_exist('/tmp/bob-the-builder/')


def get_base_build_directory():
    return mkdir_if_not_exist(os.path.join(get_base_directory(), 'builds'))


def get_settings(git_repo_name):

    settings = _load_settings_file()
    for setting_key in settings:
        if setting_key == git_repo_name:
            return settings[setting_key]

    raise BobTheBuilderException('settings for {0} was not found'.format(git_repo_name))


def get_email_settings():

    settings = _load_settings_file()
    if 'email' in settings:
        return settings['email']

    return None


def get_basic_auth():

    settings = _load_settings_file()
    if 'basic_auth' in settings:
        return settings['basic_auth'].get('login', 'admin'), \
               settings['basic_auth'].get('password', 'admin')

    return 'admin', 'admin'