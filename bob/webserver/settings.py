import os
import yaml
from os.path import expanduser


def load_settings():
    path = os.path.join(expanduser("~"), '.bob/webserver-settings.yml')
    if not os.path.isfile(path):
        return {}
    with open(path, 'r') as f:
        return yaml.load(f)


