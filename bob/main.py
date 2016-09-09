from github_webhook import Webhook
from flask import Flask, render_template, request, jsonify, redirect
import json
import bob.db as db
from datatables import ColumnDT, DataTables
import os
from bob.basic_auth import requires_auth
import traceback

app = Flask(__name__)  # Standard Flask app
webhook = Webhook(app) # Defines '/postreceive' endpoint


@app.errorhandler(500)
def internal_server_error(error):
    print 'Server Error: {0}'.format(error)
    traceback.print_exc()
    return 'Server Error: {0}'.format(error), 500


@app.errorhandler(Exception)
def unhandled_exception(e):
    print 'Unhandled Exception: {0}'.format(e)
    traceback.print_exc()
    return 'Unhandled Exception: {0}'.format(e), 500


@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
  return response


@app.route('/')
@app.route('/view/tasks')
def view_tasks():
    return render_template('view_tasks.html',
                           columns=['Id',
                                    'Git Repo',
                                    'Branch',
                                    'Tag',
                                    'Status',
                                    'Created',
                                    'Action'])


@app.route('/datatable/tasks')
def datatable_tasks():

    query = db.get_session().query(db.BuildTask).filter(db.BuildTask.id > 0)

    response = DataTables(request.args,
                          db.BuildTask,
                          query,
                          columns=[ColumnDT('id'),
                                   ColumnDT('git_repo_owner_name'),
                                   ColumnDT('git_branch'),
                                   ColumnDT('git_tag'),
                                   ColumnDT('status'),
                                   ColumnDT('created'),
                                   ColumnDT('id')]).output_result()

    # returns what is needed by DataTable
    return jsonify(response)


def _tail_log(path, lines=50, default=None):
    if os.path.exists(path):
        import subprocess
        return subprocess.check_output(['tail', path, '-n ' + str(lines)], shell=False)
    return default


@app.route('/')
@app.route('/view/tasks/<taskId>')
@requires_auth
def view_task(taskId):

    query = db.get_session().query(db.BuildTask).filter(db.BuildTask.id == taskId)

    if query.count() != 1:
        return 'Not Found', 404

    db_task = query[0]

    details = {
        'git_repo_owner_name': db_task.git_repo_owner_name,
        'git_branch': db_task.git_branch,
        'git_tag': db_task.git_tag,
        'status': db_task.status,
        'created': db_task.created,
        'build_path': db_task.build_path
    }

    from settings import get_settings
    settings = get_settings(db_task.git_repo_owner_name)
    if settings:
        details.update(settings)

    if 'docker_hub' in details and 'password' in details['docker_hub']:
        details['docker_hub']['password'] = '****'

    if 'git_hub' in details and 'password' in details['git_hub']:
        details['git_hub']['password'] = '****'

    build_log_path = os.path.join( db_task.build_path, 'docker-compose-build.log')
    run_log_path = os.path.join( db_task.build_path, 'docker-compose-run.log')
    push_log_path = os.path.join( db_task.build_path, 'docker-push.log')

    return render_template('view_task.html',
                           details=details,
                           build_log_path=build_log_path,
                           build_log_tail=_tail_log(build_log_path),
                           run_log_path=run_log_path,
                           run_log_tail=_tail_log(run_log_path),
                           push_log_path=push_log_path,
                           push_log_tail=_tail_log(push_log_path)
                           )


@app.route('/actions/task/<taskId>/rebuild')
@requires_auth
def actions_task_rebuild(taskId):

    sesson = db.get_session()
    query = sesson.query(db.BuildTask).filter(db.BuildTask.id == taskId)

    if query.count() != 1:
        return 'Not Found', 404

    db_task = query[0]
    db_task.status = 'pending'
    sesson.commit()

    return redirect("/view/tasks", code=302)


@app.route('/actions/task/<taskId>/cancel')
@requires_auth
def actions_task_cancel(taskId):

    sesson = db.get_session()
    query = sesson.query(db.BuildTask).filter(db.BuildTask.id == taskId)

    if query.count() != 1:
        return 'Not Found', 404

    db_task = query[0]

    if db_task.status == 'building':
        return 'Cannot cancel a building task yet, SORRY in the TODOs<br/><a href="/">GO BACK</a>', 500

    if db_task.status == 'pending':
        db_task.status = 'cancelled'
        sesson.commit()

    return redirect("/view/tasks", code=302)


@app.route('/build')
@requires_auth
def build():
    db.create_build_task('metocean/gregc', None, 'master')
    return 'OK', 200


@webhook.hook(event_type='create')        # Defines a handler for the 'push' event
def on_create(data):
    with open('test.create.json', 'w') as f:
        f.write(json.dumps(data))
    print json.dumps(data)


@webhook.hook(event_type='push')        # Defines a handler for the 'push' event
def on_create(data):
    with open('test.push.json', 'w') as f:
        f.write(json.dumps(data))
    print json.dumps(data)

from builder import start_builders

start_builders()
app.run()
