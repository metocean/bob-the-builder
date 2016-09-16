import datetime
import json
from dateutil.parser import parse as parse_date


class State(object):
    pending = 'pending'
    downloading = 'downloading'
    building = 'building'
    testing = 'testing'
    pushing = 'pushing'
    cancel = 'cancel'
    canceled = 'canceled'
    successful = 'successful'
    failed = 'failed'


class Task(object):
    def __init__(self,
                 git_repo,
                 git_branch='master',
                 git_tag='latest'):

        self.git_repo = git_repo
        self.git_branch = git_branch
        self.git_tag = git_tag
        self.status = 'pending'
        self.status_message = 'task has been created and is pending'
        self.events = []
        self.logs = []
        self.created_at = datetime.datetime.utcnow()
        self.modified_at = self.created_at

    def __repr__(self):
        return json.dumps(Task.to_dict(self), indent=2)

    def is_done(self):
        return self.status in (State.canceled, State.successful, State.failed)

    def get_status_message(self):
        if self.status_message:
            return self.status_message
        return ''

    def run_time(self):
        if self.is_done():
            return self.modified_at - self.created_at
        return datetime.datetime.utcnow() - self.created_at

    @staticmethod
    def from_json(text):
        return Task.from_dict(json.loads(text))

    @staticmethod
    def from_dict(dict):
        task = Task(git_repo=dict['git_repo'],
                    git_branch=dict['git_branch'],
                    git_tag=dict['git_tag'])
        task.status = dict['status']
        task.status_message = dict.get('status_message')
        task.events = dict.get('events', [])
        task.logs = dict.get('logs', [])
        task.created_at = parse_date(dict['created_at'])
        task.modified_at = parse_date(dict['modified_at'])
        return task

    def to_dict(self):
        result = {
                'git_repo': self.git_repo,
                'git_branch': self.git_branch,
                'git_tag': self.git_tag,
                'status': self.status,

                'created_at': self.created_at.isoformat(),
                'modified_at': self.modified_at.isoformat()
            }

        if self.status_message:
            result['status_message'] = self.status_message

        if self.events:
            result['events'] = self.events

        if self.logs:
            result['logs'] = self.logs

        return result


class Build(object):
    def __init__(self,
                 git_repo,
                 git_branch='master'):
        self.git_repo = git_repo
        self.git_branch = git_branch
        self.docker_compose = {}
        self.git_hub_login = {}
        self.docker_hub_login = {}
        self.notification_emails = []

    def set_git_hub_login(self, login, password):
        self.git_hub_login = {
            'login': login,
            'password': password
        }

    def set_docker_hub_login(self, login, password):
        self.docker_hub_login = {
            'login': login,
            'password': password
        }

    def set_docker_compose_build(self,
                                 docker_compose_file='docker-compose.yml',
                                 test_service=None):
        self.docker_compose['docker_compose_file'] = docker_compose_file
        self.docker_compose['test_service'] = test_service

    def set_service_to_push(self, service_name, docker_image):
        self.docker_compose['services_to_push'][service_name] = docker_image

    def __repr__(self):
        return json.dumps(Build.to_dict(self), indent=2)

    @staticmethod
    def from_dict(dict):
        build = Build(
            git_repo=dict['git_repo'],
            git_branch=dict['git_branch'])
        build.docker_compose = dict.get('docker_compose', {})
        build.git_hub_login = dict.get('git_hub_login', {})
        build.docker_hub_login = dict.get('docker_hub_login', {})
        build.notification_emails = dict.get('notification_emails', [])
        return build

    def to_dict(self):
        result = {
            'git_repo': self.git_repo,
            'git_branch': self.git_branch,
            'git_tag': self.git_tag
        }

        if self.docker_compose and len(self.docker_compose) > 0:
            result['docker_compose'] = self.docker_compose

        if self.git_hub_login and len(self.git_hub_login) > 0:
            result['git_hub_login'] = self.git_hub_login

        if self.docker_hub_login and len(self.docker_hub_login) > 0:
            result['docker_hub_login'] = self.docker_hub_login

        if self.notification_emails and len(self.notification_emails) > 0:
            result['notification_emails'] = self.notification_emails

        return result
