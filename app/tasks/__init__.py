from celery.task.control import inspect
from celery.result import AsyncResult

from .polarion import submit_to_polarion

def get_workers():
    workers = inspect(['celery@localhost']).active()
    if workers is None:
        return {}
    return workers.items()

def get_task_status(task_uuid):
    res = AsyncResult(task_uuid)
    rerutn ({
        'name': task['name'],
        'id': task['id'],
        'state': res.state,
        'meta': res.info
    })

def get_running_tasks_status():
    task_status = []
    for worker, tasks in get_workers():
        for task in tasks:
            res = AsyncResult(task['id'])
            task_status.append({
                'name': task['name'],
                'id': task['id'],
                'state': res.state,
                'meta': res.info
            })
    return task_status

def cancel_task(task_id):
    res = AsyncResult(task_id)
    res.revoke(terminate=True)
    return {
        'state': res.state,
        'meta': res.info,
        'cancelled': True
    }

def cancel_all_tasks():
    task_status = get_running_tasks_status()
    for task in task_status:
        cancel_task(task['id'])
        task['cancelled'] = True
    return task_status
