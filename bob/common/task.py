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
                 git_tag='latest',
                 created_by=None,
                 ):
        self.git_repo = git_repo
        self.git_branch = git_branch if git_branch else 'master'
        self.git_tag = git_tag if git_tag else 'latest'
        self.events = []
        self.logs = []
        self.created_at = datetime.datetime.utcnow()
        self.created_by = created_by
        self.modified_at = self.created_at
        self.builder_ipaddress = None
        self.builder_hostname = None
        self.state = None
        self.state_message = None
        self.set_state(State.pending, 'task is waiting to be processed')

    def __repr__(self):
        return json.dumps(Task.to_dict(self), indent=2)

    def is_done(self):
        return self.state in (State.canceled, State.successful, State.failed)

    def get_state_message(self):
        if self.state_message:
            return self.state_message
        return ''

    def get_builder_hostname(self):
        if self.builder_hostname:
            return self.builder_hostname
        return ''

    def get_builder_ipaddress(self):
        if self.builder_ipaddress:
            return self.builder_ipaddress
        return ''

    def get_created_by(self):
        if self.created_by:
            return self.created_by
        return ''

    def get_duration(self):
        if len(self.events) <= 1:
            from_date = self.created_at
            to_date = datetime.datetime.utcnow()
        # self.events[0] will always be pending,
        # we want to ignore pending in as a part of duration.
        elif not self.is_done():
            from_date = parse_date(self.events[1]['created_at'])
            to_date = datetime.datetime.utcnow()
        else:
            from_date = parse_date(self.events[1]['created_at'])
            to_event = self.events[-1]
            if to_event['finished_at'] is None:
                to_date = parse_date(to_event['created_at'])
            else:
                to_date = parse_date(to_event['finished_at'])
        return ':'.join(str(to_date - from_date).split(':')[:2])

    def set_state(self, state, message=None):
        now = datetime.datetime.utcnow()

        # set the last events run time
        if len(self.events) > 0:
            event = self.events[-1]
            event['finished_at'] = now.isoformat()
            event['duration'] = str(now - parse_date(event['created_at']))

        # make new event
        event = {'state': state,
                 'state_message': message,
                 'created_at': now.isoformat(),
                 'finished_at': None,
                 'duration': None}

        self.state = state
        self.state_message = message
        self.events.append(event)

    def get_events(self):
        for event in self.events:
            duration = event['duration']
            if duration is None:
                duration = str(datetime.datetime.utcnow() - parse_date(event['created_at']))
            yield {
                'state': event['state'],
                'created_at': event['created_at'],
                'state_message': event['state_message'] if event['state_message'] is not None else '',
                'finished_at': event['finished_at'] if event['finished_at'] is not None else '',
                'duration': duration
            }

    @staticmethod
    def from_json(text):
        return Task.from_dict(json.loads(text))

    @staticmethod
    def from_dict(dict):
        task = Task(git_repo=dict['git_repo'],
                    git_branch=dict['git_branch'],
                    git_tag=dict['git_tag'],
                    created_by=dict.get('created_by', None))
        task.state = dict['state']
        task.state_message = dict.get('state_message')
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
                'state': self.state,
                'created_at': self.created_at.isoformat(),
                'modified_at': self.modified_at.isoformat()
            }

        if self.created_by:
            result['created_by'] = self.created_by

        if self.state_message:
            result['state_message'] = self.state_message

        if self.events:
            result['events'] = self.events

        if self.logs:
            result['logs'] = self.logs

        if self.builder_ipaddress:
            result['builder_ipaddress'] = self.builder_ipaddress

        if self.builder_hostname:
            result['builder_hostname'] = self.builder_hostname

        return result

    def save_log(self, text, log_path, insert_first=False):
        import os
        if not text or len(text) == 0:
            return

        filename = os.path.basename(log_path)

        entry = {'filename': filename,
                 'path:': log_path,
                 'text': text,
                 'created_at': datetime.datetime.utcnow().isoformat()}

        index = -1
        for i, entree in enumerate(self.logs):
            if entree['filename'] == filename:
                index = i
                break

        if index < 0:
            if insert_first:
                self.logs.insert(0, entry)
            else:
                self.logs.append(entry)
        else:
            self.logs[index] = entry

