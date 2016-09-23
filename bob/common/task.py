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
        self.git_branch = git_branch if git_branch else 'master'
        self.git_tag = git_tag if git_tag else 'latest'
        self.status = 'pending'
        self.status_message = 'task has been created and is pending'
        self.events = []
        self.logs = []
        self.created_at = datetime.datetime.utcnow()
        self.modified_at = self.created_at
        self.builder_ipaddress = None
        self.builder_hostname = None

    def __repr__(self):
        return json.dumps(Task.to_dict(self), indent=2)

    def is_done(self):
        return self.status in (State.canceled, State.successful, State.failed)

    def get_status_message(self):
        if self.status_message:
            return self.status_message
        return ''

    def get_builder_hostname(self):
        if self.builder_hostname:
            return self.builder_hostname
        return ''

    def get_builder_ipaddress(self):
        if self.builder_ipaddress:
            return self.builder_ipaddress
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
        task.builder_ipaddress = dict.get('builder_ipaddress', None)
        task.builder_hostname = dict.get('builder_hostname', None)
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

        if self.builder_ipaddress:
            result['builder_ipaddress'] = self.builder_ipaddress

        if self.builder_hostname:
            result['builder_hostname'] = self.builder_hostname

        return result
