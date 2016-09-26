import os
from os.path import expanduser


def find_settings_file(filename):
    path = os.path.join(expanduser("~/.bob"), filename)
    if os.path.exists(path):
        return path

    path = os.path.join('/opt/bob/etc', filename)
    if os.path.exists(path):
        return path

    path = os.path.join('/usr/local/etc/bob', filename)
    if os.path.exists(path):
        return path

    path = os.path.join('/etc/bob', filename)
    if os.path.exists(path):
        return path
