from settings import get_settings
import os
from shutil import rmtree
from bob.exceptions import BobTheBuilderException
from bob.tools import execute, mkdir_p
from bob.email_tools import send_email
from bob.git_hub import download_branch_source, download_release_source
import bob.docker_hub as docker_hub
import bob.db as db
import multiprocessing
from time import sleep


def _docker_compose_build(tag_name,
                          source_path,
                          output_path,
                          src_path,
                          repo_settings):

    build_filename = repo_settings['docker_compose'].get('docker_compose_file', 'docker-compose.yml')
    build_file_path = os.path.join(source_path, build_filename)

    if not os.path.exists(build_file_path):
        raise BobTheBuilderException('Could find a docker compose file "{0}" to build'.format(build_file_path))

    print 'docker-compose: build'
    os.chdir(src_path)
    build_log_file_path = os.path.join(output_path, 'docker-compose-build.log')
    execute('docker-compose -f {0} build --no-cache --pull --force-rm'.format(build_filename),build_log_file_path)

    run_test_service = repo_settings['docker_compose'].get('run_test_service')
    if not run_test_service:
        print 'docker-compose: push'
        docker_hub.push(tag_name, build_log_file_path, output_path, repo_settings)

    else:
        try:
            print 'docker-compose: run'
            os.chdir(src_path)
            execute('docker-compose -f {0} run {1}'.format(build_filename, run_test_service),
                    os.path.join(output_path, 'docker-compose-run.log'))

            print 'docker-compose: push'
            docker_hub.push(tag_name, build_log_file_path, output_path, repo_settings)

        finally:
            print 'docker-compose: down'
            os.chdir(src_path)
            execute('docker-compose -f {0} down --remove-orphans --volumes --rmi local'.format(build_filename),
                     os.path.join(output_path, 'docker-compose-down.log'))


def _print_result(repo_settings, repo_name, git_tag_name, git_branch, subject, body=None):
    if not git_tag_name:
        git_tag_name = git_branch

    if not body:
        body = subject

    subject = subject.format(tag=git_tag_name, repo=repo_name)
    body = body.format(tag=git_tag_name, repo=repo_name)

    if 'notification_email' in repo_settings:
        send_email(repo_settings['notification_email'], subject, body)

    print body


def build_repo(task, db_session):

    try:
        repo_settings = get_settings(task.git_repo_owner_name)

        git_hub_login = repo_settings['git_hub'].get('login')
        git_hub_password = repo_settings['git_hub'].get('password')

        if os.path.exists(task.build_path):
            rmtree(task.build_path)
        mkdir_p(task.build_path)

        if task.git_tag:
            source_path = download_release_source(task.git_repo_owner_name,
                                                  task.git_tag,
                                                  task.build_path,
                                                  git_hub_login,
                                                  git_hub_password)
        else:
            source_path = download_branch_source(repo_owner_name=task.git_repo_owner_name,
                                                  output_path=task.build_path,
                                                  branch=task.git_branch,
                                                  login=git_hub_login,
                                                  password=git_hub_password)

        _docker_compose_build(task.git_tag,
                              source_path,
                              task.build_path,
                              source_path,
                              repo_settings)

        _print_result(repo_settings,
                      task.git_repo_owner_name,
                      task.git_tag,
                      task.git_branch,
                      'BobTheBuilder Successfully built "{repo}:{tag}"')

        task.status = 'successful'
        db_session.commit()

    except Exception as ex:

        subject = 'BobTheBuilder failed to build "{repo}:{tag}"'
        body = subject
        body += '\r\n\r\n'
        body += ex.message
        body += '\r\n'

        _print_result(repo_settings,
                      task.git_repo_owner_name,
                      task.git_tag,
                      task.git_branch,
                      subject,
                      body)

        task.status = 'failed'
        db_session.commit()


class BuildProcess(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)

    def run(self):
        while True:
            session = db.get_session()

            task = db.next_build_task(session)
            if not task:
                sleep(1)
                continue
            try:
                print 'proc {0} building: {1}'.format(
                    self.name,
                    str(task))

                build_repo(task, session)
            except:
                import sys
                print sys.exc_info()


def start_builders():

    from docker_client import clean_all_networks
    clean_all_networks()

    session = db.get_session()
    query = session.query(db.BuildTask).filter(
        (db.BuildTask.status == 'building') | (db.BuildTask.status == 'pending'))

    if query.count() > 0:
        for task in query:
            task.status = 'cancelled'
        session.commit()

    _builders = None
    _builder_count = 1
    print 'Creating %d builders' % _builder_count
    _builders = [BuildProcess() for i in xrange(_builder_count)]
    for b in _builders:
        b.start()
