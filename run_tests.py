#!/usr/bin/env python

import coverage
import django
import optparse
import os
import sys

from django.conf import settings


if not settings.configured:
    try:
        from django.contrib.auth.tests.custom_user import CustomUser
        has_custom_user = True
    except ImportError:
        has_custom_user = False
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': 'django_fitapp',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.messages',
            'django.contrib.sessions',
            'fitapp',
        ],
        SECRET_KEY='something-secret',
        ROOT_URLCONF='fitapp.urls',

        FITAPP_CONSUMER_KEY='',
        FITAPP_CONSUMER_SECRET='',
        # In >= Django 1.6, we can use a custom user model
        AUTH_USER_MODEL='auth.CustomUser' if has_custom_user else 'auth.User'
    )


# In Django >= 1.7, we need to run setup first
if hasattr(django, 'setup'):
    django.setup()


from django.contrib.auth.management import create_superuser
from django.db.models import signals
from django.test.utils import get_runner


def run_tests():
    parser = optparse.OptionParser()
    parser.add_option('--coverage', dest='coverage', default='2',
                      help="coverage level, 0=no coverage, 1=without branches,"
                      " 2=with branches")
    options, tests = parser.parse_args()
    tests = tests or ['fitapp']
    
    covlevel = int(options.coverage)
    if covlevel:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if covlevel == 2:
            branch = True
        else:
            branch = False
        cov = coverage.coverage(branch=branch, config_file='.coveragerc')
        cov.load()
        cov.start()

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True, failfast=False)
    try:
        # Workaround a bug in Django >= 1.7 that causes a testrunner failure
        # when using CustomUser
        from django.apps import apps
        signals.post_migrate.disconnect(
            create_superuser, sender=apps.get_app_config('auth'),
            dispatch_uid="django.contrib.auth.management.create_superuser")
    except ImportError:
        pass
    exit_val = test_runner.run_tests(tests)

    if covlevel:
        cov.stop()
        cov.save()
    
    sys.exit(exit_val)


if __name__ == '__main__':
    run_tests()
