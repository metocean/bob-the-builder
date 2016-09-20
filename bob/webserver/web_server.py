from github_webhook import Webhook
from flask import Flask, render_template, request
from gunicorn.app.base import BaseApplication
from gunicorn.six import iteritems
import multiprocessing
import traceback
from dateutil.parser import parse as parse_date

from bob.common.entities import State
from bob.common import db
from bob.common import queues
from bob.common.entities import Task

import os


app = Flask(__name__)  # Standard Flask app
webhook = Webhook(app)  # Defines '/postreceive' endpoint


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


@app.route('/')
def tasks_view():
    return render_template('tasks.html', tasks=db.load_all_tasks())


@app.route('/task/<owner>/<repo>/<branch>/<tag>/<created_at>', methods=['GET'])
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


@app.route('/task/<owner>/<repo>/<branch>/<tag>/<created_at>', methods=['POST'])
def task_action(owner, repo, branch, tag, created_at):

    if request.form['action'] == 'cancel':
        task = db.load_task(git_repo=owner + '/' + repo,
                            git_branch=branch,
                            git_tag=tag,
                            created_at=parse_date(created_at))

        task.status = State.cancel
        db.save_task(task)

        return 'CANCELED'

    return 'FAILED'


@webhook.hook(event_type='release')
def github_webhook(data):

    if not ('repository' in data and 'fullname' in data['repository']):
        return 'OK', 200

    if not ('action' in data and data['action'] == 'published'):
        return 'OK', 200

    if not ('release' in data and 'tag_name' in data['release'] and 'target_commitish' in data['release']):
        return 'OK', 200

    repo = data['repository']['fullname']
    branch = data['release']['target_commitish']
    tag = data['release']['tag_name']

    task = Task(git_repo=repo, git_branch=branch, git_tag=tag)
    db.save_task(task)
    queues.enqueue_task(task)

    print("Got push with: {0}".format(data))
    return 'OK', 200


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


if __name__ == "__main__":
    db.create_task_table()
    queues._create_task_queue()

    options = {
        'bind': '%s:%s' % ('0.0.0.0', os.environ.get('BOB-BUILDER-PORT', '8080')),
        'workers': multiprocessing.cpu_count(),
    }
    GunicornApplication(app, options).run()