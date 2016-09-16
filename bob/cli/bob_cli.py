from bob.common import db
from bob.common import queues
from bob.common import entities

task = entities.Task(git_repo='metocean/gregc')
db.db_save_task(task)
queues.enqueue_task(task)


