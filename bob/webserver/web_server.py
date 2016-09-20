from github_webhook import Webhook
from flask import Flask, render_template, request
import bob.common.db as db
from bob.webserver.basic_auth import requires_auth
import traceback
from dateutil.parser import parse as parse_date
from bob.common.entities import State


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
    return render_template('tasks.html', tasks=db.db_load_all_tasks())


@app.route('/task/<owner>/<repo>/<branch>/<tag>/<created_at>', methods=['GET'])
def task_view(owner, repo, branch, tag, created_at):

    task = db.db_load_task(git_repo=owner + '/' + repo,
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
        task = db.db_load_task(git_repo=owner + '/' + repo,
                               git_branch=branch,
                               git_tag=tag,
                               created_at=parse_date(created_at))

        task.status = State.cancel
        db.db_save_task(task)

        return 'CANCELED'

    return 'FAILED'


app.run()
