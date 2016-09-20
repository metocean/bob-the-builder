import os
import yaml
from os.path import expanduser
from bob.worker.tools import mkdir_if_not_exist


def load_settings():
    path = os.path.join(expanduser("~"), '.bob/webserver-settings.yml')
    if not os.path.isfile(path):
        return {}
    with open(path, 'r') as f:
        return yaml.load(f)


