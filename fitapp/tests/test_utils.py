from collections import OrderedDict

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import override_settings
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

    @override_settings(FITAPP_SUBSCRIPTIONS=OrderedDict([('bogus', [])]))
    def test_invalid_subscriptions_category_error(self):
        """
        Check that having an invalid category key in the FITAPP_SUBSCRIPTIONS
        setting raises an ImproperlyConfigured error
        """
        self.assertRaises(ImproperlyConfigured, get_setting,
                          'FITAPP_SUBSCRIPTIONS')

    @override_settings(FITAPP_SUBSCRIPTIONS='BOGUS')
    def test_invalid_subscriptions_type_error(self):
        """
        Check that setting FITAPP_SUBSCRIPTIONS to an invalid type results in
        an ImproperlyConfigured error
        """
        self.assertRaises(ImproperlyConfigured, get_setting,
                          'FITAPP_SUBSCRIPTIONS')

    @override_settings(FITAPP_SUBSCRIPTIONS=OrderedDict([
        ('foods', ['steps'])
    ]))
    def test_invalid_subscriptions_resource_error(self):
        """
        Check that having an invalid resource in the FITAPP_SUBSCRIPTIONS
        setting raises an ImproperlyConfigured error
        """
        self.assertRaises(ImproperlyConfigured, get_setting,
                          'FITAPP_SUBSCRIPTIONS')

    @override_settings(FITAPP_SUBSCRIPTIONS=OrderedDict([
        ('activities', ['steps'])
    ]))
    def test_invalid_subscriptions_no_error(self):
        """
        Check that get_setting doesn't raise an error when FITAPP_SUBSCRIPTIONS
        is valid
        """
        subs = get_setting('FITAPP_SUBSCRIPTIONS')

        self.assertEqual(subs['activities'], ['steps'])
