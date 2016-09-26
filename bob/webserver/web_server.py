from flask import Flask, render_template, request, Response, jsonify
from gunicorn.app.base import BaseApplication
from gunicorn.six import iteritems
import multiprocessing
import traceback
from dateutil.parser import parse as parse_date
from functools import wraps
from bob.common.task import Task
from bob.common import db
from bob.common import queues
from bob.webserver.settings import load_settings
import hashlib
import hmac
import sys
import os


app = Flask(__name__)
settings = load_settings()

if settings and 'basic_auth' in settings:
    app.config['login'] = settings['basic_auth']['login']
    app.config['password'] = settings['basic_auth']['password']

if settings and 'github_hook' in settings:
    app.config['secret'] = settings['github_hook'].get('secret')


def _queue_build(repo, branch, tag, created_by):
    task = Task(git_repo=repo,
                git_branch=branch,
                git_tag=tag,
                created_by=created_by)
    db.save_task(task)
    queues.enqueue_task(task)


def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == app.config['username'] and password == app.config['password']


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_basic_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if 'username' in app.config and (not auth or not check_auth(auth.username, auth.password)):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


@app.errorhandler(500)
def internal_server_error(error):
    print('Server Error: {0}'.format(error))
    traceback.print_exc()
    return 'Server Error: {0}'.format(error), 500


@app.errorhandler(Exception)
def unhandled_exception(e):
    print('Unhandled Exception: {0}'.format(e))
    traceback.print_exc()
    return 'Unhandled Exception: {0}'.format(e), 500


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response


@app.route('/', methods=['GET', 'POST'])
@requires_basic_auth
def tasks_view():
    if request.method == 'POST' and 'repo' in request.form:
        _queue_build(repo=request.form['repo'], created_by='website')
    return render_template('tasks.html', tasks=db.load_all_tasks())


@app.route('/task/<owner>/<repo>/<branch>/<tag>/<created_at>', methods=['GET'])
@requires_basic_auth
def task_view(owner, repo, branch, tag, created_at):

    task = db.load_task(git_repo=owner + '/' + repo,
                        git_branch=branch,
                        git_tag=tag,
                        created_at=parse_date(created_at))

    if not task:
        return 'Task not found', 404

    cancel_disabled = 'disabled' if task.is_done() else ''

    return render_template('task.html',
                           task=task,
                           cancel_disabled=cancel_disabled)


def _verify_hmac_hash(data, signature, secret):
    if sys.version_info[0] != 2 and isinstance(secret, str):
        secret = bytearray(secret, 'utf-8')
    mac = hmac.new(secret, msg=data, digestmod=hashlib.sha1)
    return hmac.compare_digest('sha1=' + mac.hexdigest(), signature)


@app.route("/github_webhook", methods=['POST'])
def github_payload():
    # delivery = request.headers.get('X-GitHub-Delivery')
    event_type = request.headers.get('X-GitHub-Event')
    signature = request.headers.get('X-Hub-Signature')
    secret = app.config.get('secret')

    if request.data is None:
        return jsonify(msg='post data is missing'), 400

    if secret:
        if signature is None:
            return jsonify(msg='Unauthorized, X-Hub-Signature was not found in headers'), 401

        elif not _verify_hmac_hash(request.data, signature, bytes(secret, 'UTF-8')):
            return jsonify(msg='Unauthorized, X-Hub-Signature did not match secret'), 401

    if event_type is None:
        return jsonify(msg='X-GitHub-Event was missing'), 400

    if event_type.lower() == "release":
        data = request.get_json()

        if not ('repository' in data and 'full_name' in data['repository']):
            return jsonify({'msg': 'Ok'})

        if not ('action' in data and data['action'] == 'published'):
            return jsonify({'msg': 'Ok'})

        if not ('release' in data and 'tag_name' in data['release'] and 'target_commitish' in data['release']):
            return jsonify({'msg': 'Ok'})

        repo = data['repository']['full_name']
        branch = data['release']['target_commitish']
        tag = data['release']['tag_name']

        created_by = 'github'
        if 'author' in data['release'] and 'login' in data['release']['author']:
            created_by += ' - {0}'.format(data['release']['author']['login'])

        _queue_build(repo=repo, branch=branch, tag=tag, created_by=created_by)

    return jsonify({'msg': 'Ok'})


class GunicornApplication(BaseApplication):

    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super(GunicornApplication, self).__init__()

    def load_config(self):
        config = dict([(key, value) for key, value in iteritems(self.options)
                       if key in self.cfg.settings and value is not None])
        for key, value in iteritems(config):
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def main():
    db.create_task_table()
    queues.create_task_queue()

    options = {
        'bind': '%s:%s' % ('0.0.0.0', os.environ.get('BOB-BUILDER-PORT', '8080')),
        'workers': multiprocessing.cpu_count(),
    }
    GunicornApplication(app, options).run()


if __name__ == "__main__":
    main()
