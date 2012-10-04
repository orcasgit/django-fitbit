from mock import patch
import random
import string

from django.conf import settings
from django.contrib.auth.models import User
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

    def setUp(self):
        super(TestFitbitRetrieval, self).setUp()
        self.fb = self.create_fitbit(**self.fbuser.get_user_data())

    @patch.object(Fitbit, 'time_series')
    def mock_error(self, error, time_series=None):
        time_series.side_effect = error
        return utils.get_fitbit_steps(self.fbuser, '30d')

    @patch.object(Fitbit, 'time_series')
    def mock_response(self, response, time_series=None):
        time_series.return_value = response
        return utils.get_fitbit_steps(self.fbuser, '30d')

    def test_value_error(self):
        """ValueError from the Fitbit.time_series should propagate."""
        error = ValueError('')
        with self.assertRaises(error.__class__) as c:
            self.mock_error(error)

    def test_unauthorized(self):
        """HTTPUnauthorized from the Fitbit.time_series should propagate."""
        error = fitbit_exceptions.HTTPUnauthorized('')
        with self.assertRaises(error.__class__) as c:
            self.mock_error(error)

    def test_forbidden(self):
        """HTTPForbidden from the Fitbit.time_series should propagate."""
        error = fitbit_exceptions.HTTPForbidden('')
        with self.assertRaises(error.__class__) as c:
            self.mock_error(error)

    def test_not_found(self):
        """HTTPNotFound from the Fitbit.time_series should propagate."""
        error = fitbit_exceptions.HTTPNotFound('')
        with self.assertRaises(error.__class__) as c:
            self.mock_error(error)

    def test_conflict(self):
        """HTTPConflict from the Fitbit.time_series should propagate."""
        error = fitbit_exceptions.HTTPConflict('')
        with self.assertRaises(error.__class__) as c:
            self.mock_error(error)

    def test_server_error(self):
        """HTTPServerError from the Fitbit.time_series should propagate."""
        error = fitbit_exceptions.HTTPServerError('')
        with self.assertRaises(error.__class__) as c:
            self.mock_error(error)

    def test_bad_request(self):
        """HTTPBadRequest from the Fitbit.time_series should propagate."""
        error = fitbit_exceptions.HTTPBadRequest('')
        with self.assertRaises(error.__class__) as c:
            self.mock_error(error)

    def test_retrieval(self):
        response = {'activities-steps': [1,2,3]}
        steps = self.mock_response(response)
        self.assertEquals(steps, response['activities-steps'])
