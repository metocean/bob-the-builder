import os
from os.path import expanduser
from bob.common.exceptions import BobTheBuilderException


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

    raise BobTheBuilderException(
        'cannot find settings file {0} in\r\n~/.bob\r\n/opt/bob/etc\r\n/usr/local/etc/bob\r\n/etc/bob'.format(
            filename))
