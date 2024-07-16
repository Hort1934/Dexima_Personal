import os
from celery import Celery
from celery.schedules import crontab


# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dexima_ats_web_service.settings')

app = Celery('dexima_ats_web_service')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'subscription_updater': {
        'task': 'main_service.tasks.subscription_updater',
        'schedule': crontab(minute=0),
    },
    # 314-DB2Range
    'assets_range_calculator': {
        'task': 'main_service.tasks.assets_range_calculator',
        'schedule': crontab(minute=30, hour='*/3'),
    },
}

app.conf.update(
    result_expires=70000,
)
