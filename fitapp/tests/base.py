from mock import patch, Mock
import random
import string
from urllib import urlencode

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from fitbit.api import Fitbit

from fitapp.models import UserFitbit


class MockClient(object):

    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id', None)
        self.error = kwargs.get('error', None)
        self.key = kwargs.get('key', None)
        self.secret = kwargs.get('secret', None)

    def authorize_token_url(self, *args, **kwargs):
        return '/test'

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
    TEST_SERVER = 'http://testserver'

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

    def assertRedirectsNoFollow(self, response, url, status_code=302):
        """
        Workaround to test whether a response redirects to another URL without
        loading the page at that URL.
        """
        self.assertEquals(response.status_code, status_code)
        full_url = self.TEST_SERVER + url
        self.assertEquals(response._headers['location'][1], full_url)


    def _get(self, url_name=None, url_kwargs=None, get_kwargs=None, **kwargs):
        """Convenience wrapper for test client GET request."""
        url_name = url_name or self.url_name
        url = reverse(url_name, kwargs=url_kwargs)  # Base URL.

        # Add GET parameters.
        if get_kwargs:
            url += '?' + urlencode(get_kwargs)

        return self.client.get(url, **kwargs)

    def _set_session_vars(self, **kwargs):
        session = self.client.session
        for key, value in kwargs.items():
            session[key] = value
        try:
            session.save()  # Only available on authenticated sessions.
        except AttributeError:
            pass

    @patch('fitbit.api.FitbitOauthClient')
    def _mock_client(self, client=None, **kwargs):
        client.return_value = MockClient(**kwargs)
        return self._get()

    @patch('fitapp.utils.get_fitbit_steps')
    def _mock_utility(self, utility=None, error=None, response=None):
        if error:
            utility.side_effect = error('')
        elif response:
            utility.return_value = response
        return self._get()
