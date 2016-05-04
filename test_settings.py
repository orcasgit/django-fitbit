import sys


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'django_fitapp',
    }
}
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'fitapp',
]
SECRET_KEY = 'something-secret'
ROOT_URLCONF = 'fitapp.urls'

FITAPP_CONSUMER_KEY = ''
FITAPP_CONSUMER_SECRET = ''
FITAPP_SUBSCRIBE = True
FITAPP_SUBSCRIBER_ID = 1

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
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True
    },
]

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)
