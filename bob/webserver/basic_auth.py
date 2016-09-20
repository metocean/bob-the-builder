from functools import wraps
from flask import request, Response
from bob.webserver.settings import load_settings

_settings = None


def _check_auth(username, password):
    settings = load_settings()
    if 'login' in settings and 'password' in settings:
        return username == settings['login'] and password == settings['password']
    return True


def _authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not _check_auth(auth.username, auth.password):
            return _authenticate()
        return f(*args, **kwargs)
    return decorated
