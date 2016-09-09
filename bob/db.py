from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import os
from bob.tools import LockFile
from bob.settings import get_base_directory
from bob.settings import get_base_build_directory


Base = declarative_base()


class BuildTask(Base):
    __tablename__ = 'task'
    id = Column(Integer, primary_key=True)
    git_repo_owner_name = Column(String)
    git_branch = Column(String)
    git_tag = Column(String)
    build_path = Column(String)
    status = Column(String)
    created = Column(DateTime)
    lock_file = None

    def lock(self, session):
        if not self.lock_file:
            self.lock_file = LockFile(os.path.join(self.build_path, 'lock'))
        if self.lock_file.try_acquire():
            try:
                self.status = 'building'
                session.commit()
            except Exception:
                self.lock_file.release()
                return False
            return True
        return False

    def release(self):
        if self.lock_file:
            self.release()

    def __repr__(self):
        return json.dumps({
            'git_repo_owner_name': self.git_repo_owner_name,
            'git_branch': self.git_branch,
            'git_tag': self.git_tag,
            'build_path': self.build_path,
            'status': self.status,
            'created': str(self.created),
        }, indent=2)


class BuildEvent(Base):
    __tablename__ = 'event'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    status = Column(String)
    created = Column(DateTime)

    def __repr__(self):
        return json.dumps({
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'created': str(self.created),
        }, indent=2)



def get_session():
    engine = create_engine('sqlite:///' +
                           os.path.join(get_base_directory(), 'bob-the-builder.db'),
                           echo=False)
    try:
        engine.connect()
        engine.execute('SELECT 1')
    except Exception as ex:
        Base.metadata.create_all(engine)

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def create_build_task(git_repo_owner_name, git_tag, git_branch):
    session = get_session()

    build_path = os.path.join(get_base_build_directory(),
                              git_repo_owner_name,
                              git_branch,
                              git_tag if git_tag else 'latest')

    session.add(BuildTask(git_repo_owner_name=git_repo_owner_name,
                          git_branch=git_branch,
                          git_tag=git_tag,
                          build_path=build_path,
                          status='pending',
                          created=datetime.utcnow()))
    session.commit()


def next_build_task(session):

    for task in session.query(BuildTask)\
            .order_by(BuildTask.id):

        if task.status != 'pending':
            continue

        if task.lock(session):
            return task

    return None


def get_all_tasks(session):
    return session.query(BuildTask).order_by(BuildTask.id)
