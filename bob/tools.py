import errno
import os
import fcntl
import subprocess
import pycurl
import json
from bob.exceptions import BobTheBuilderException


class LockFile(object):
    def __init__(self, file_path, lock_on_with=True):
        self._file_path = file_path
        self._fd = None
        self._lock_on_with = lock_on_with

    def __enter__(self):
        if self._lock_on_with:
            self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def try_acquire(self):
        '''
        :return: Returns True if the lock was acquired otherwise it returns False.
        '''
        if not os.path.exists(os.path.dirname(self._file_path)):
            mkdir_p(os.path.dirname(self._file_path))

        if not self._fd:
            self._fd = os.open(self._file_path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)

        try:
            fcntl.lockf(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            pass

        os.close(self._fd)
        self._fd = None
        return False

    def acquire(self):
        '''
        waits until the file lock is acquired.
        '''
        if not self._fd:
            self._fd = os.open(self._file_path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY)

        fcntl.lockf(self._fd, fcntl.LOCK_EX)

    def release(self):
        if not self._fd:
            return

        fcntl.lockf(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None

    def close(self):
        self.release()


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def mkdir_if_not_exist(path):
    if not os.path.exists(path):
        mkdir_p(path)
    return path


def execute(cmd, logfile):

    with open(logfile, 'w') as log:
        error_code = subprocess.call(cmd, shell=True, universal_newlines=True, stdout=log, stderr=log)
        if error_code:
            raise BobTheBuilderException('"{0}" exited with {1} check logfile for details {2}'.format(
                cmd,
                error_code,
                logfile))


def url_download(url, filepath, auth_username=None, auth_password=None):
    status = None
    with open(filepath, 'wb') as f:
        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.WRITEDATA, f)
        curl.setopt(pycurl.FOLLOWLOCATION, True)
        if auth_username and auth_password:
            curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
            curl.setopt(pycurl.USERPWD, "%s:%s" % (auth_username, auth_password))
        curl.perform()
        status = curl.getinfo(pycurl.HTTP_CODE)
        curl.close()
    return status


def url_get_utf8(url, auth_username=None, auth_password=None):

    status = None
    content = None
    try:
        # Python 3
        from io import BytesIO
    except ImportError:
        # Python 2
        from StringIO import StringIO as BytesIO

    try:
        buffer = BytesIO()

        curl = pycurl.Curl()
        curl.setopt(pycurl.URL, url)
        curl.setopt(pycurl.WRITEDATA, buffer)
        curl.setopt(pycurl.FOLLOWLOCATION, True)
        if auth_username and auth_password:
            curl.setopt(pycurl.HTTPAUTH, pycurl.HTTPAUTH_BASIC)
            curl.setopt(pycurl.USERPWD, "%s:%s" % (auth_username, auth_password))
        curl.perform()

        status = curl.getinfo(pycurl.HTTP_CODE)
        content = buffer.getvalue().decode('utf-8')

    finally:
        buffer.close()
        curl.close()

    return status, content


def url_get_json(url, auth_username=None, auth_password=None):

    status, content = url_get_utf8(url, auth_username, auth_password)
    if not content:
        return status, None

    return status, json.loads(content)
