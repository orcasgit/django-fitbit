from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings


# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitapp.defaults')

app = Celery('fitapp_tests')
app.conf['CELERY_ALWAYS_EAGER'] = True
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS, force=True)
