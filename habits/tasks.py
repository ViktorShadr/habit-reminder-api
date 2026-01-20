from celery import shared_task

@shared_task
def ping_task():
    print("PING from Celery!")
