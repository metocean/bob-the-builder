import os
import yaml
from os.path import expanduser
from bob.common.tools import mkdir_if_not_exist


def load_settings():
    with open(os.path.join(expanduser("~"), '.bob/worker-settings.yml'), 'r') as f:
        return yaml.load(f)


def get_base_build_path():
    path = os.path.join(expanduser("~"), 'bob/builds/')
    mkdir_if_not_exist(path)
    return path

