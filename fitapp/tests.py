import json
from mock import patch
import random
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from fitbit import exceptions as fitbit_exceptions
from fitbit.api import Fitbit

from .models import UserFitbit
from . import utils


class FitappTestBase(TestCase):

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


class TestFitbitIntegration(FitappTestBase):
    """Tests for the is_integrated utility function."""

    def test_is_integrated(self):
        """Users with stored OAuth information are integrated."""
        self.assertTrue(utils.is_integrated(self.user))

    def test_is_not_integrated(self):
        """User is not integrated if we have no OAuth data for them."""
        UserFitbit.objects.all().delete()
        self.assertFalse(utils.is_integrated(self.user))

    def test_other_user_is_integrated(self):
        """utils.is_integrated can be called on any user."""
        user2 = self.create_user()
        fbuser2 = self.create_userfitbit(user=user2)
        self.assertTrue(utils.is_integrated(user2))

    def test_other_user_is_not_integrated(self):
        """utils.is_integrated can be called on any user."""
        user2 = self.create_user()
        self.assertFalse(utils.is_integrated(user2))


class TestFitbitRetrieval(FitappTestBase):
    """Tests for the get_fitbit_steps utility function."""

    def setUp(self):
        super(TestFitbitRetrieval, self).setUp()
        self.fb = self.create_fitbit(**self.fbuser.get_user_data())

    @patch.object(Fitbit, 'time_series')
    def mock_time_series(self, time_series=None, error=None, response=None):
        if error:
            time_series.side_effect = error('')
        if response:
            time_series.return_value = response
        return utils.get_fitbit_steps(self.fbuser, '30d')

    def _error_test(self, error):
        with self.assertRaises(error) as c:
            self.mock_time_series(error=error)

    def test_value_error(self):
        """ValueError from the Fitbit.time_series should propagate."""
        self._error_test(ValueError)

    def test_unauthorized(self):
        """HTTPUnauthorized from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPUnauthorized)

    def test_forbidden(self):
        """HTTPForbidden from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPForbidden)

    def test_not_found(self):
        """HTTPNotFound from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPNotFound)

    def test_conflict(self):
        """HTTPConflict from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPConflict)

    def test_server_error(self):
        """HTTPServerError from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPServerError)

    def test_bad_request(self):
        """HTTPBadRequest from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPBadRequest)

    def test_retrieval(self):
        response = {'activities-steps': [1,2,3]}
        steps = self.mock_time_series(response=response)
        self.assertEquals(steps, response['activities-steps'])


class TestGetSteps(FitappTestBase):
    """Tests for the get_steps view."""
    url_name = 'fitbit-steps'
    valid_periods = ['1d', '7d', '30d', '1w', '1m', '3m', '6m', '1y', 'max']

    def setUp(self):
        super(TestGetSteps, self).setUp()
        self.period = '30d'

    @patch('fitapp.utils.get_fitbit_steps')
    def mock_utility(self, utility=None, error=None, response=None):
        if error:
            utility.side_effect = error('')
        if response:
            utility.return_value = response
        return self._get()

    def _get(self):
        url = reverse(self.url_name, kwargs={'period': self.period})
        return self.client.get(url)

    def test_not_authenticated(self):
        """View should return 404 when user isn't logged in."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 404)

    def test_not_active(self):
        """View should return 404 when user isn't active."""
        self.user.is_active = False
        self.user.save()
        response = self._get()
        self.assertEquals(response.status_code, 404)

    def test_not_integrated(self):
        """View should return 401 when user is not integrated."""
        self.fbuser.delete()
        response = self._get()
        self.assertEquals(response.status_code, 401)

    def test_bad_fitbit_data(self):
        """View should return 403 when user integration is invalid."""
        response = self.mock_utility(error=fitbit_exceptions.HTTPUnauthorized)
        self.assertEquals(response.status_code, 403)

        response = self.mock_utility(error=fitbit_exceptions.HTTPForbidden)
        self.assertEquals(response.status_code, 403)

    def test_bad_period(self):
        """View should return 400 when invalid period is given."""
        self.period = 'bad'
        response = self._get()
        self.assertEquals(response.status_code, 400)

    def test_rate_limited(self):
        """View should return 409 when Fitbit rate limit is hit."""
        response = self.mock_utility(error=fitbit_exceptions.HTTPConflict)
        self.assertEquals(response.status_code, 409)

    def test_fitbit_error(self):
        """View should return 502 when Fitbit server error occurs."""
        response = self.mock_utility(error=fitbit_exceptions.HTTPServerError)
        self.assertEquals(response.status_code, 502)

    def test_retrieval(self):
        """View should return JSON steps data."""
        steps = [{'dateTime': '2000-01-01', 'value': 10}]
        for period in self.valid_periods:
            self.period = period
            response = self.mock_utility(response=steps)
            error_msg = 'Should be able to retrieve data for {0}.'.format(
                    self.period)
            self.assertEquals(response.status_code, 200, error_msg)
            self.assertEquals(response.content, json.dumps(steps), error_msg)
