from __future__ import absolute_import

from fitapp.tests.test_retrieval import *
from fitapp.tests.test_integration import *

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app
