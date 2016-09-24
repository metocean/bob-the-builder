import json
import os
import pycurl
import subprocess
import smtplib
from email.mime.text import MIMEText
from bob.worker.settings import load_settings
from bob.common.exceptions import BobTheBuilderException
import socket


def execute(cmd, logfile=None):

    if logfile:
        with open(logfile, 'w') as log:
            error_code = subprocess.call(cmd, shell=True, universal_newlines=True, stdout=log, stderr=log)
            if error_code:
                raise BobTheBuilderException('"{0}" exited with {1} check logfile for details {2}'.format(
                    cmd,
                    error_code,
                    logfile))
    else:
        error_code = subprocess.call(cmd, shell=True, universal_newlines=True)
        if error_code:
            raise BobTheBuilderException('"{0}" exited with {1}'.format(cmd, error_code))


def tail(filename, num_of_lines=10, tail_cmd_timeout=15):
    """
    returns the tail of the given file.
    :param filename: the filename / path you wish to return the tail of
    :param num_of_lines: the number of lines you wish to tail.
    :param tail_cmd_timeout: how long to wait before giving up on the tail request.
    :return: returns None if the file tail Timeout.
    """
    try:
        return subprocess.check_output(['tail',
                                        '-{0}'.format(num_of_lines),
                                        filename],
                                       universal_newlines=True,
                                       timeout=tail_cmd_timeout)
    except subprocess.TimeoutExpired:
        return None
    except subprocess.CalledProcessError:
        return None


def execute_with_logging(cmd,
                         log_filename,
                         tail_callback,
                         tail_callback_obj,
                         num_of_lines=100,
                         tail_interval=5):
    """
    executes the shell process with logging.
    :param cmd: the shell command to execute
    :param log_filename: the filename / path where you wish the log to be stored
    :param tail_callback: this call back function is called with the tail for the given log file.
    :param num_of_lines: the number of lines to tail in the log callback
    :param tail_interval: the interval between tail_callback()s.
    """
    with open(log_filename, 'w') as log:
        proc = subprocess.Popen(cmd,
                                shell=True,
                                universal_newlines=True,
                                stdout=log,
                                stderr=log)
        while proc.returncode is None:
            try:
                proc.wait(tail_interval)
            except subprocess.TimeoutExpired:
                pass
            lines = tail(log_filename, num_of_lines)
            if tail_callback and lines:
                tail_callback(lines, log_filename, tail_callback_obj)

        if proc.returncode != 0:
            raise Exception('"{cmd}" exited with {returncode} check logfile for details {log_filename}\r\n {lines}'.format(
                cmd=cmd,
                returncode=proc.returncode,
                log_filename=log_filename,
                lines=lines))


def url_download(url, filepath, auth_username=None, auth_password=None):
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


def send_email(to_address, subject, body):
    settings = load_settings()
    if not (settings and 'email' in settings
            and 'host' in settings['email']
            and 'from' in settings['email']):
        return

    host = settings['email']['host']
    port = settings['email'].get('port', 25)
    from_address = settings['email']['from']
    debug = settings['email'].get('debug', False)
    starttls = settings['email'].get('starttls', False)
    login = settings['email'].get('login')
    password = settings['email'].get('password')

    server = smtplib.SMTP(host, port)

    if debug:
        server.set_debuglevel(debug)

    if starttls:
        server.ehlo()
        server.starttls()

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_address
    msg['To'] = ','.join(to_address)

    if login and password:
        server.login(login, password)

    server.sendmail(from_address, to_address, msg.as_string())
    server.quit()


def get_ipaddress():
    try:
        return [l for l in ([ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1], [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]) if l][0][0]
    except:
        return ''


def get_hostname():
    try:
        return socket.gethostname()
    except:
        return ''
