import random
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase

from fitapp.models import UserFitbit
from fitapp import utils


class FitappTestBase(TestCase):

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


class TestFitappUtils(FitappTestBase):

    def setUp(self):
        self.username = self.random_string(25)
        self.password = self.random_string(25)
        self.user = self.create_user(username=self.username,
                password=self.password)
        self.fbuser = self.create_userfitbit(user=self.user)

        self.client.login(username=self.username, password=self.password)

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
