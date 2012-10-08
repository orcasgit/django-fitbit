from mock import patch, Mock
import random
import string
from urllib import urlencode

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from fitbit import exceptions as fitbit_exceptions
from fitbit.api import Fitbit

from fitapp.models import UserFitbit


class MockClient(object):

    def __init__(self, **kwargs):
        self.user_id = kwargs['user_id'] if 'user_id' in kwargs else None
        self.error = kwargs['error'] if 'error' in kwargs else None
        self.key = kwargs['key'] if 'key' in kwargs else None
        self.secret = kwargs['secret'] if 'secret' in kwargs else None

    def authorize_token_url(self, *args, **kwargs):
        return reverse('test')

    def fetch_request_token(self, *args, **kwargs):
        return None

    def fetch_access_token(self, *args, **kwargs):
        if self.error:
            raise self.error('')
        response = Mock(['key', 'secret'])
        response.key = self.key
        response.secret = self.secret
        return response


class FitappTestBase(TestCase):
    urls = 'fitapp.tests.urls'

    def setUp(self):
        self.username = self.random_string(25)
        self.password = self.random_string(25)
        self.user = self.create_user(username=self.username,
                password=self.password)
        self.fbuser = self.create_userfitbit(user=self.user)

        self.client.login(username=self.username, password=self.password)

    def random_string(self, length=255, extra_chars=''):
        chars = string.letters + extra_chars
        return ''.join([random.choice(chars) for i in range(length)])

    def create_user(self, username=None, email=None, password=None, **kwargs):
        username = username or self.random_string(25)
        email = email or '{0}@{1}.com'.format(self.random_string(25),
                self.random_string(10))
        password = password or self.random_string(25)
        user = User.objects.create_user(username, email, password)
        User.objects.filter(pk=user.pk).update(**kwargs)
        user = User.objects.get(pk=user.pk)
        return user

    def create_userfitbit(self, **kwargs):
        defaults = {
            'user': kwargs.pop('user', self.create_user()),
            'fitbit_user': self.random_string(25),
            'auth_token': self.random_string(25),
            'auth_secret': self.random_string(25),
        }
        defaults.update(kwargs)
        return UserFitbit.objects.create(**defaults)

    def create_fitbit(self, **kwargs):
        defaults = {
            'consumer_key': self.random_string(25),
            'consumer_secret': self.random_string(25),
        }
        defaults.update(kwargs)
        return Fitbit(**defaults)

    def assert_correct_redirect(self, response, url_name):
        url = 'http://testserver' + reverse(url_name)
        self.assertEquals(response._headers['location'][1], url)

    def _get(self, url_name=None, url_kwargs=None, **kwargs):
        """Convenience wrapper for test client get request."""
        url_name = url_name or self.url_name
        url_kwargs = url_kwargs or {}
        url = reverse(url_name, kwargs=url_kwargs)
        if kwargs:
            url += '?' + urlencode(kwargs)
        return self.client.get(url)

    @patch('fitbit.api.FitbitOauthClient')
    def mock_client(self, client=None, **kwargs):
        client.return_value = MockClient(**kwargs)
        return self._get()
