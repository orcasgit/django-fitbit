#!/usr/bin/env python

import optparse
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
            'djcelery',
            'fitapp',
        ],
        SECRET_KEY='something-secret',
        ROOT_URLCONF='fitapp.urls',

        FITAPP_CONSUMER_KEY='',
        FITAPP_CONSUMER_SECRET='',

        LOGGING = {
            'version': 1,
            'handlers': {
                'null': {
                    'level': 'DEBUG',
                    'class': 'django.utils.log.NullHandler',
                },
            },
            'loggers': {
                'fitapp.tasks': {'handlers': ['null'], 'level': 'DEBUG'},
            },
        },
        TEST_RUNNER = 'djcelery.contrib.test_runner.CeleryTestSuiteRunner'
    )


from django.test.utils import get_runner

def run_tests():
    parser = optparse.OptionParser()
    _, tests = parser.parse_args()
    tests = tests or ['fitapp']

    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True, failfast=False)
    sys.exit(test_runner.run_tests(tests))


if __name__ == '__main__':
    run_tests()
