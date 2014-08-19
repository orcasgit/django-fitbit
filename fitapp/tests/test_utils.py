from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from fitbit import Fitbit

from fitapp.utils import create_fitbit, get_setting


class TestFitappUtilities(TestCase):
    def test_create_fitbit(self):
        """
        Check that the create_fitbit utility creates a Fitbit object and
        produces an error is raised when the consumer key or secret aren't set.
        """
        with self.settings(FITAPP_CONSUMER_KEY=None,
                           FITAPP_CONSUMER_SECRET=None):
            self.assertRaises(ImproperlyConfigured, create_fitbit)
        with self.settings(FITAPP_CONSUMER_KEY='',
                           FITAPP_CONSUMER_SECRET=None):
            self.assertRaises(ImproperlyConfigured, create_fitbit)
        with self.settings(FITAPP_CONSUMER_KEY=None,
                           FITAPP_CONSUMER_SECRET=''):
            self.assertRaises(ImproperlyConfigured, create_fitbit)
        self.assertEqual(type(create_fitbit()), Fitbit)

    def test_get_setting_error(self):
        """
        Check that an error is raised when trying to get a nonexistent setting.
        """
        self.assertRaises(ImproperlyConfigured, get_setting, 'DOES_NOT_EXIST')
