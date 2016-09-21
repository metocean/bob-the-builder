import json

from botocore.exceptions import ClientError
from bob.common.aws import get_boto3_resource

from bob.worker.aws_helpers import error_code_equals

_task_queue_name = 'bob-task'
_task_cancel_queue_name = 'bob-task-cancel'


def _queue_exists(queue_name, sqs):
    try:
        queue = sqs.get_queue_by_name(QueueName=queue_name)
        print(queue.url)
        return True
    except ClientError as err:
        if error_code_equals(err, 'AWS.SimpleQueueService.NonExistentQueue'):
            return False
        raise err


def _create_task_queue(sqs=get_boto3_resource('sqs')):
    if _queue_exists(_task_queue_name, sqs=sqs):
        return
    sqs.create_queue(QueueName=_task_queue_name,
                     Attributes={'VisibilityTimeout': '60',
                                 'ReceiveMessageWaitTimeSeconds': '15'})


def _create_task_cancel_queue(sqs=get_boto3_resource('sqs')):
    if _queue_exists(_task_queue_name, sqs=sqs):
        return
    sqs.create_queue(QueueName=_task_queue_name,
                     Attributes={'VisibilityTimeout': '60',
                                 'ReceiveMessageWaitTimeSeconds': '15'})


def enqueue_task(task, sqs=get_boto3_resource('sqs')):
    queue = sqs.get_queue_by_name(QueueName=_task_queue_name)
    queue.send_message(MessageBody=str(task))


def get_task_queue(sqs=get_boto3_resource('sqs')):
    return sqs.get_queue_by_name(QueueName=_task_queue_name)


def enqueue_cancel(task, sqs=get_boto3_resource('sqs')):

    queue = sqs.get_queue_by_name(QueueName=_task_cancel_queue_name)
    queue.send_message(MessageBody=json.dumps(
        {'git_repo': task.git_repo,
         'git_branch': task.git_branch,
         'git_tag': task.git_tag,
         'created_at': task.created_at}))


def get_task_queue(sqs=get_boto3_resource('sqs')):
    return sqs.get_queue_by_name(QueueName=_task_queue_name)
