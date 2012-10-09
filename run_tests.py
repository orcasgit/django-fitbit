#!/usr/bin/env python

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
    )


from django.test.utils import get_runner

def run_tests():
    TestRunner = get_runner(settings)
    test_runner = TestRunner(verbosity=1, interactive=True, failfast=False)
    sys.exit(test_runner.run_tests(['fitapp']))


if __name__ == '__main__':
    run_tests()
