from datetime import datetime

import boto3

from bob.common.entities import Build
from bob.common.entities import Task
from bob.worker.aws_helpers import error_code_equals

_task_table_name = 'bob-task'
_build_table_name = 'bob-build'


def _table_exists(table_name):
    client = boto3.client('dynamodb')
    try:
      print(client.describe_table(TableName=table_name))
      return True
    except Exception as e:
        if error_code_equals(e, 'ResourceNotFoundException'):
            return False
        raise e


def _db_create_task_table(db=boto3.resource('dynamodb')):
    """
    creates a new table if it does not exits, blocks until it does.
    :param db: boto3.resource('dynamodb')
    """
    if _table_exists(_task_table_name):
        return

    table = db.create_table(
        TableName=_task_table_name,
        KeySchema=[
            {
                'AttributeName': 'git_repo',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'key',
                'KeyType': 'RANGE'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'git_repo',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'key',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )
    # Wait until the table exists.
    table.meta.client.get_waiter('table_exists').wait(TableName=_task_table_name)
    print('table {0} created'.format(_task_table_name))


def db_save_task(task, db=boto3.resource('dynamodb')):
    table = db.Table(_task_table_name)

    task.modified_at = datetime.utcnow()
    dict = task.to_dict()
    dict['key'] = '{0}:{1}:{2}'.format(task.git_branch,
                                       task.git_tag,
                                       task.created_at.isoformat())

    table.put_item(Item=dict)


def db_load_task(git_repo,
                 git_branch,
                 git_tag,
                 created_at,
                 db=boto3.resource('dynamodb')):
    table = db.Table(_task_table_name)
    response = table.get_item(
        Key={
            'git_repo': git_repo,
            'key': '{0}:{1}:{2}'.format(git_branch,
                                        git_tag,
                                        created_at.isoformat())
        }
    )
    if 'Item' in response:
        return Task.from_dict(response['Item'])
    return None


def db_reload_task(task, db=boto3.resource('dynamodb')):
    table = db.Table(_task_table_name)
    response = table.get_item(
        Key={
            'git_repo': task.git_repo,
            'key': '{0}:{1}:{2}'.format(task.git_branch,
                                        task.git_tag,
                                        task.created_at.isoformat())
        }
    )
    return Task.from_dict(response['Item'])


def db_load_all_tasks(db=boto3.resource('dynamodb')):
    table = db.Table(_task_table_name)
    response = table.scan()
    if 'Items' in response:
        for task in response['Items']:
            yield Task.from_dict(task)


def _db_create_build_table(db=boto3.resource('dynamodb')):
    """
    creates a new table if it does not exits, blocks until it does.
    :param db: boto3.resource('dynamodb')
    """
    if _table_exists(_build_table_name):
        return

    table = db.create_table(
        TableName=_build_table_name,
        KeySchema=[
            {
                'AttributeName': 'git_repo',
                'KeyType': 'HASH'
            },
            {
                'AttributeName': 'git_branch',
                'KeyType': 'RANGE'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'git_repo',
                'AttributeType': 'S'
            },
            {
                'AttributeName': 'git_branch',
                'AttributeType': 'S'
            },
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    )
    # Wait until the table exists.
    table.meta.client.get_waiter('table_exists').wait(TableName=_build_table_name)
    print('table {0} created'.format(_build_table_name))


def db_save_build(build, db=boto3.resource('dynamodb')):
    table = db.Table(_build_table_name)
    table.put_item(Item=build.to_dict())


def db_load_build(git_repo, git_branch, db=boto3.resource('dynamodb')):
    table = db.Table(_build_table_name)
    response = table.get_item(
        Key={
            'git_repo': git_repo,
            'git_branch': git_branch
        }
    )
    if 'Item' in response:
        return Build.from_dict(response['Item'])
    return None


def db_load_all_builds(db=boto3.resource('dynamodb')):
    table = db.Table(_build_table_name)
    response = table.scan()
    if 'Items' in response:
        for build in response['Items']:
            yield Build.from_dict(build)


print('creating AWS DynamoDB tables')
_db_create_task_table()
_db_create_build_table()
