import os
import yaml
from bob.common.settings import find_settings_file
import boto3


def _load_settings():
    file_path = find_settings_file('aws-settings.yml')
    if not os.path.isfile(file_path):
        return None
    with open(file_path, 'r') as f:
        return yaml.load(f)


def get_boto3_session():
    settings = _load_settings()
    if not settings:
        return boto3.session.Session(profile_name='default')
    return boto3.session.Session(aws_access_key_id=settings['aws_access_key_id'],
                                 aws_secret_access_key=settings['aws_secret_access_key'],
                                 region_name=settings['region_name'])


def get_boto3_resource(resource_name):
    return get_boto3_session().resource(resource_name)
