from datetime import datetime

from boto3.dynamodb.conditions import Attr
from bob.common.aws import get_boto3_resource, get_boto3_session

from bob.common.task import Task, State
from bob.worker.aws_helpers import error_code_equals

_task_table_name = 'bob-task'


def _table_exists(table_name):
    client = get_boto3_session().client('dynamodb')
    try:
      print(client.describe_table(TableName=table_name))
      return True
    except Exception as e:
        if error_code_equals(e, 'ResourceNotFoundException'):
            return False
        raise e


def create_task_table(db=get_boto3_resource('dynamodb')):
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


def save_task(task, db=get_boto3_resource('dynamodb')):
    table = db.Table(_task_table_name)

    task.modified_at = datetime.utcnow()
    dict = task.to_dict()
    dict['key'] = '{0}:{1}:{2}'.format(task.git_branch,
                                       task.git_tag,
                                       task.created_at.isoformat())

    table.put_item(Item=dict)


def load_task(git_repo,
              git_branch,
              git_tag,
              created_at,
              db=get_boto3_resource('dynamodb')):
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


def reload_task(task, db=get_boto3_resource('dynamodb')):
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


def load_all_tasks(db=get_boto3_resource('dynamodb')):
    table = db.Table(_task_table_name)
    response = table.scan()
    if 'Items' in response:
        for task in response['Items']:
            yield Task.from_dict(task)


def tasks_ps(db=get_boto3_resource('dynamodb')):
    table = db.Table(_task_table_name)
    db_filter = (Attr('status').eq(State.pending)
                 | Attr('status').eq(State.downloading)
                 | Attr('status').eq(State.building)
                 | Attr('status').eq(State.testing)
                 | Attr('status').eq(State.pushing))
    response = table.scan(FilterExpression=db_filter)
    if 'Items' in response:
        for task in response['Items']:
            yield Task.from_dict(task)
