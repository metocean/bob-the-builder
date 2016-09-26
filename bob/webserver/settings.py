import os
import yaml
from os.path import expanduser
from bob.common.settings import find_settings_file

def load_settings():
    path = find_settings_file('webserver-settings.yml')
    if not os.path.isfile(path):
        return {}
    with open(path, 'r') as f:
        return yaml.load(f)
