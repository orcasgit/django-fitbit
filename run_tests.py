#!/usr/bin/env python

import coverage
import optparse
import os
import sys

from django.conf import settings


if not settings.configured:
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
        FITAPP_SUBSCRIBE=True,
        FITAPP_SUBSCRIBER_ID=1,

        LOGGING = {
            'version': 1,
            'handlers': {
                'null': {
                    'level': 'DEBUG',
                    'class': '%s.NullHandler' % (
                        'logging' if sys.version_info[0:2] > (2,6)
                        else 'django.utils.log'),
                },
            },
            'loggers': {
                'fitapp.tasks': {'handlers': ['null'], 'level': 'DEBUG'},
            },
        },

        MIDDLEWARE_CLASSES = (
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        )
    )


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
    exit_val = test_runner.run_tests(tests)

    if covlevel:
        cov.stop()
        cov.save()

    sys.exit(exit_val)


import django
# In Django 1.7, we need to run setup first
if hasattr(django, 'setup'):
    django.setup()


if __name__ == '__main__':
    run_tests()
