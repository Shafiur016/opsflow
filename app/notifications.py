"""Optional Celery worker; queue delivery is enabled only with ENABLE_NOTIFICATIONS=1."""
import os
import logging
try:
    from celery import Celery
except ImportError:
    Celery = None

celery_app = Celery('opsflow', broker=os.getenv('REDIS_URL', 'redis://redis:6379/0')) if Celery else None
if celery_app:
    celery_app.conf.update(task_acks_late=True, broker_connection_retry_on_startup=True)
    @celery_app.task(name='opsflow.notify', autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
    def notify(tenant_id: int, task_id: int, status: str):
        # Integration point: replace structured notification logs with email/webhook delivery.
        logging.getLogger('opsflow').info('task_notification tenant=%s task=%s status=%s', tenant_id, task_id, status)

def enqueue_notification(tenant_id: int, task_id: int, status: str):
    if os.getenv('ENABLE_NOTIFICATIONS') != '1':
        return
    if celery_app is None:
        raise RuntimeError('Celery is required for ENABLE_NOTIFICATIONS=1')
    celery_app.send_task('opsflow.notify', args=[tenant_id, task_id, status])
