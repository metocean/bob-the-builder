import errno
import json
import os
import pycurl
import subprocess

from bob.common.exceptions import BobTheBuilderException


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


def rename_basedir(dir_path, new_basename):
    if dir_path.endswith('/'):
        basedir = os.path.split(os.path.split(dir_path)[0])[1]
        new_path = os.path.join(dir_path[:dir_path.rindex(basedir)-1], new_basename) + '/'
    else:
        basedir = os.path.split(dir_path)[1]
        new_path = os.path.join(dir_path[:dir_path.rindex(basedir)-1], new_basename)
    os.rename(dir_path, new_path)
    return new_path


def base_dirname(dir_path):
    # if not os.path.isdir(dir_path):
    #     return None
    if dir_path.endswith('/'):
        return os.path.split(os.path.split(dir_path)[0])[1]
    else:
        return os.path.split(dir_path)[1]



# import smtplib
# from email.mime.text import MIMEText
# from bob.settings import get_email_settings
#
# def send_email(to_address, subject, body):
#
#     settings = get_email_settings()
#     if not settings:
#         return
#
#     server = smtplib.SMTP(settings['host'], settings['port'])
#
#     if 'debug' in settings:
#         server.set_debuglevel(bool(settings['debug']))
#
#     if 'starttls' in settings and settings['starttls']:
#         server.ehlo()
#         server.starttls()
#
#     msg = MIMEText(body)
#     msg['Subject'] = subject
#     msg['From'] = settings['from']
#     msg['To'] = ','.join(to_address)
#
#     server.login(settings['login'], settings['password'])
#     server.sendmail(settings['from'], to_address, msg.as_string())
#     server.quit()
