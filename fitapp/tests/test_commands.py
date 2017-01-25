import json
import requests_mock
import time

from django.core import management
from django.utils.six import StringIO
from fitbit.api import FitbitOauth2Client
from mock import patch
from requests_oauthlib import OAuth2Session

from fitapp.models import UserFitbit
from fitapp.management.commands import refresh_tokens

from .base import FitappTestBase


class TestCommands(FitappTestBase):
    """Tests for Fitapp management commands."""

    def test_refresh_tokens_command(self):
        """Test the refresh_tokens command."""

        out = StringIO()
        management.call_command('refresh_tokens', stdout=out)

        self.assertIn('Successfully refreshed 0 tokens', out.getvalue())

        self.fbuser.expires_at -= 300
        self.fbuser.save()
        out = StringIO()
        with requests_mock.mock() as m:
            m.post(FitbitOauth2Client.refresh_token_url, text=json.dumps({
                'access_token': 'fake_access_token',
                'refresh_token': 'fake_refresh_token',
                'expires_at': time.time() + 300,
            }))
            management.call_command('refresh_tokens', stdout=out)
        self.fbuser = UserFitbit.objects.get()

        self.assertIn('Successfully refreshed 1 tokens', out.getvalue())
        self.assertEqual('fake_access_token', self.fbuser.access_token)
        self.assertEqual('fake_refresh_token', self.fbuser.refresh_token)
        self.assertTrue(self.fbuser.expires_at > time.time())

        out = StringIO()
        with requests_mock.mock() as m:
            m.post(FitbitOauth2Client.refresh_token_url, text=json.dumps({
                'access_token': 'fake_access_token2',
                'refresh_token': 'fake_refresh_token2',
                'expires_at': time.time() + 300,
            }))
            management.call_command('refresh_tokens', all=True, stdout=out)
        self.fbuser = UserFitbit.objects.get()

        self.assertIn('Successfully refreshed 1 tokens', out.getvalue())
        self.assertEqual('fake_access_token2', self.fbuser.access_token)
        self.assertEqual('fake_refresh_token2', self.fbuser.refresh_token)
        self.assertTrue(self.fbuser.expires_at > time.time())

        out = StringIO()
        with requests_mock.mock() as m:
            m.post(FitbitOauth2Client.refresh_token_url, text=json.dumps({
                'errors': [{'errorType': 'invalid_grant'}],
            }))
            management.call_command('refresh_tokens', all=True, stdout=out)

        self.assertIn('Successfully refreshed 0 tokens', out.getvalue())
        self.assertIn('Failed to refresh 1 tokens', out.getvalue())

        out = StringIO()
        with requests_mock.mock() as m:
            m.post(FitbitOauth2Client.refresh_token_url, text=json.dumps({
                'errors': [{'errorType': 'invalid_grant'}],
            }))
            management.call_command('refresh_tokens', all=True, deauth=True, stdout=out)

        self.assertIn('Successfully refreshed 0 tokens', out.getvalue())
        self.assertIn('Failed to refresh 1 tokens', out.getvalue())
        self.assertIn('Deauthenticated 1 users', out.getvalue())
        self.assertEqual(0, UserFitbit.objects.count())
