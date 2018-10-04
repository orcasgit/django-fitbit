import json
import time
from collections import OrderedDict
from datetime import datetime

import requests_mock
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.test.utils import override_settings
from django.urls import reverse
from fitbit.exceptions import HTTPConflict
from freezegun import freeze_time
from mock import patch
from requests.auth import _basic_auth_str

from fitapp import utils
from fitapp.decorators import fitbit_integration_warning
from fitapp.models import TimeSeriesDataType, UserFitbit
from fitapp.tasks import subscribe, unsubscribe
from .base import FitappTestBase


class TestIntegrationUtility(FitappTestBase):

    def test_is_integrated(self):
        """Users with stored OAuth information are integrated."""
        self.assertTrue(utils.is_integrated(self.user))

    def test_is_not_integrated(self):
        """User is not integrated if we have no OAuth data for them"""
        UserFitbit.objects.all().delete()
        self.assertFalse(utils.is_integrated(self.user))

    def test_unauthenticated(self):
        """User is not integrated if they aren't logged in."""
        user = AnonymousUser()
        self.assertFalse(utils.is_integrated(user))


class TestIntegrationDecorator(FitappTestBase):

    def setUp(self):
        super(TestIntegrationDecorator, self).setUp()
        self.fake_request = HttpRequest()
        self.fake_request.user = self.user
        self.fake_view = lambda request: "hello"
        self.messages = []

    def _mock_decorator(self, msg=None):
        def mock_error(request, message, *args, **kwargs):
            self.messages.append(message)

        with patch.object(messages, 'error', mock_error) as error:
            return fitbit_integration_warning(msg=msg)(self.fake_view)(
                self.fake_request)

    def test_unauthenticated(self):
        """Message should be added if user is not logged in."""
        self.fake_request.user = AnonymousUser()
        results = self._mock_decorator()

        self.assertEqual(results, "hello")
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0], utils.get_setting('FITAPP_DECORATOR_MESSAGE'))

    def test_is_integrated(self):
        """Decorator should have no effect if user is integrated."""
        results = self._mock_decorator()

        self.assertEqual(results, "hello")
        self.assertEqual(len(self.messages), 0)

    def test_is_not_integrated(self):
        """Message should be added if user is not integrated."""
        UserFitbit.objects.all().delete()
        results = self._mock_decorator()

        self.assertEqual(results, "hello")
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(
            self.messages[0], utils.get_setting('FITAPP_DECORATOR_MESSAGE'))

    def test_custom_msg(self):
        """Decorator should support a custom message string."""
        UserFitbit.objects.all().delete()
        msg = "customized"
        results = self._mock_decorator(msg)

        self.assertEqual(results, "hello")
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(self.messages[0], "customized")

    def test_custom_msg_func(self):
        """Decorator should support a custom message function."""
        UserFitbit.objects.all().delete()
        msg = lambda request: "message to {0}".format(request.user)
        results = self._mock_decorator(msg)

        self.assertEqual(results, "hello")
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(self.messages[0], msg(self.fake_request))


class TestLoginView(FitappTestBase):
    url_name = 'fitbit-login'

    def test_get(self):
        """
        Login view should generate a token_url and then
        redirect to an authorization URL.
        """
        response = self._mock_client()
        self.assertRedirectsNoFollow(response, '/complete/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserFitbit.objects.count(), 1)

    def test_unauthenticated(self):
        """User must be logged in to access Login view."""
        self.client.logout()
        response = self._get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserFitbit.objects.count(), 1)

    def test_unintegrated(self):
        """Fitbit credentials not required to access Login view."""
        self.fbuser.delete()
        response = self._mock_client()
        self.assertRedirectsNoFollow(response, '/complete/')
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_next(self):
        response = self._mock_client(get_kwargs={'next': '/next'})
        self.assertRedirectsNoFollow(response, '/complete/')
        self.assertEqual(self.client.session.get('fitbit_next', None), '/next')
        self.assertEqual(UserFitbit.objects.count(), 1)


class TestCompleteView(FitappTestBase):
    url_name = 'fitbit-complete'
    user_id = 'userid'
    token = {
        'access_token': 'AccessToken123',
        'refresh_token': 'RefreshToken123',
        'expires_at': time.time() + 300,
        'user_id': user_id
    }
    code = 'Code123'

    def setUp(self):
        super(TestCompleteView, self).setUp()
        self.fbuser.delete()

    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_complete(self, tsd_apply_async, sub_apply_async):
        """Complete view should fetch & store user's access credentials."""
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})
        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        fbuser = UserFitbit.objects.get()
        sub_apply_async.assert_called_once_with(
            (fbuser.fitbit_user, settings.FITAPP_SUBSCRIBER_ID), countdown=5)
        tsdts = TimeSeriesDataType.objects.all()
        self.assertEqual(tsd_apply_async.call_count, tsdts.count())
        for i, _type in enumerate(tsdts):
            tsd_apply_async.assert_any_call(
                (fbuser.fitbit_user, _type.category, _type.resource,),
                countdown=10 + (i * 5))
        self.assertEqual(fbuser.user, self.user)
        self.assertEqual(fbuser.access_token, self.token['access_token'])
        self.assertEqual(fbuser.refresh_token, self.token['refresh_token'])
        self.assertEqual(fbuser.fitbit_user, self.user_id)

    @override_settings(FITAPP_HISTORICAL_INIT_DELAY=11)
    @override_settings(FITAPP_BETWEEN_DELAY=6)
    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_complete_different_delays(self, tsd_apply_async, sub_apply_async):
        """Complete view should use configured delays"""
        tsdts = TimeSeriesDataType.objects.all()
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})
        fbuser = UserFitbit.objects.get()

        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        for i, _type in enumerate(tsdts):
            tsd_apply_async.assert_any_call(
                (fbuser.fitbit_user, _type.category, _type.resource,),
                countdown=11 + (i * 6))

    @override_settings(FITAPP_SUBSCRIPTIONS=OrderedDict([]))
    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_complete_empty_subs(self, tsd_apply_async, sub_apply_async):
        """Complete view should not import data if subs dict is empty"""
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})

        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        self.assertEqual(tsd_apply_async.call_count, 0)

    @override_settings(FITAPP_SUBSCRIPTIONS=OrderedDict([('foods', [])]))
    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_complete_no_res(self, tsd_apply_async, sub_apply_async):
        """Complete view shouldn't import data if subs dict has no resources"""
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})

        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        self.assertEqual(tsd_apply_async.call_count, 0)

    @override_settings(FITAPP_SUBSCRIPTIONS=OrderedDict([
        ('foods', ['steps'])
    ]))
    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_complete_bad_resources(self, tsd_apply_async, sub_apply_async):
        """
        Complete view shouldn't import data if subs dict has invalid resources
        """
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})

        self.assertContains(
            response,
            "['steps'] resources are invalid for the foods category",
            status_code=500
        )
        self.assertEqual(tsd_apply_async.call_count, 0)

    @override_settings(FITAPP_SUBSCRIPTIONS=OrderedDict([
        ('activities', ['steps', 'calories', 'distance', 'activityCalories']),
        ('foods', ['log/water']),
    ]))
    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_complete_sub_list(self, tsd_apply_async, sub_apply_async):
        """
        Complete view should only import the listed subscriptions, in the right
        order
        """
        activities = TimeSeriesDataType.activities
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})
        fbuser = UserFitbit.objects.get()

        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        tsd_apply_async.assert_any_call(
            (fbuser.fitbit_user, activities, 'steps',), countdown=10)
        tsd_apply_async.assert_any_call(
            (fbuser.fitbit_user, activities, 'calories',), countdown=15)
        tsd_apply_async.assert_any_call(
            (fbuser.fitbit_user, activities, 'distance',), countdown=20)
        tsd_apply_async.assert_any_call(
            (fbuser.fitbit_user, activities, 'activityCalories'), countdown=25)
        tsd_apply_async.assert_any_call(
            (fbuser.fitbit_user, TimeSeriesDataType.foods, 'log/water',),
            countdown=30)

    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_complete_already_integrated(self, tsd_apply_async, sub_apply_async):
        """
        Complete view redirect to the error view if a user attempts to connect
        an already integrated fitbit user to a second user.
        """
        self.create_userfitbit(user=self.user, fitbit_user=self.user_id)
        username = '{0}2'.format(self.username)
        self.create_user(username=username, password=self.password)
        self.client.logout()
        self.client.login(username=username, password=self.password)
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEqual(UserFitbit.objects.all().count(), 1)
        self.assertEqual(sub_apply_async.call_count, 0)
        self.assertEqual(tsd_apply_async.call_count, 0)

    def test_unauthenticated(self):
        """User must be logged in to access Complete view."""
        self.client.logout()
        response = self._mock_client()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserFitbit.objects.count(), 0)

    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_next(self, tsd_apply_async, sub_apply_async):
        """
        Complete view should redirect to session['fitbit_next'] if available.
        """
        self._set_session_vars(fitbit_next='/test')
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})
        self.assertRedirectsNoFollow(response, '/test')
        fbuser = UserFitbit.objects.get()
        sub_apply_async.assert_called_once_with(
            (fbuser.fitbit_user, settings.FITAPP_SUBSCRIBER_ID), countdown=5)
        self.assertEqual(
            tsd_apply_async.call_count, TimeSeriesDataType.objects.count())
        self.assertEqual(fbuser.user, self.user)
        self.assertEqual(fbuser.access_token, self.token['access_token'])
        self.assertEqual(fbuser.refresh_token, self.token['refresh_token'])
        self.assertEqual(fbuser.expires_at, self.token['expires_at'])
        self.assertEqual(fbuser.fitbit_user, self.user_id)

    def test_access_error(self):
        """
        Complete view should redirect to error if access token is
        inaccessible.
        """
        response = self._mock_client(client_kwargs={'error': Exception})
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_no_code(self):
        """
        Complete view should redirect to error if `code` param is not
        present.
        """
        response = self._mock_client()
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_no_access_token(self):
        """
        Complete view should redirect to error if there isn't an access_token.
        """
        token = self.token.copy()
        token.pop('access_token')
        response = self._mock_client(
            client_kwargs=token, get_kwargs={'code': self.code})
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    @patch('fitapp.tasks.subscribe.apply_async')
    @patch('fitapp.tasks.get_time_series_data.apply_async')
    def test_integrated(self, tsd_apply_async, sub_apply_async):
        """Complete view should overwrite existing credentials for this user.
        """
        self.fbuser = self.create_userfitbit(user=self.user)
        response = self._mock_client(
            client_kwargs=self.token, get_kwargs={'code': self.code})
        fbuser = UserFitbit.objects.get()
        sub_apply_async.assert_called_with(
            (fbuser.fitbit_user, settings.FITAPP_SUBSCRIBER_ID), countdown=5)
        self.assertEqual(tsd_apply_async.call_count,
                         TimeSeriesDataType.objects.count())
        self.assertEqual(fbuser.user, self.user)
        self.assertEqual(fbuser.access_token, self.token['access_token'])
        self.assertEqual(fbuser.refresh_token, self.token['refresh_token'])
        self.assertEqual(fbuser.fitbit_user, self.user_id)
        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))


class TestErrorView(FitappTestBase):
    url_name = 'fitbit-error'

    def test_get(self):
        """Should be able to retrieve Error page."""
        response = self._get()
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated(self):
        """User must be logged in to access Error view."""
        self.client.logout()
        response = self._get()
        self.assertEqual(response.status_code, 302)

    def test_unintegrated(self):
        """No Fitbit credentials required to access Error view."""
        self.fbuser.delete()
        response = self._get()
        self.assertEqual(response.status_code, 200)


class TestLogoutView(FitappTestBase):
    url_name = 'fitbit-logout'

    @patch('fitapp.tasks.unsubscribe.apply_async')
    def test_get(self, apply_async):
        """Logout view should remove associated UserFitbit and redirect."""
        response = self._get()
        kwargs = self.fbuser.get_user_data()
        del kwargs['refresh_cb']
        apply_async.assert_called_once_with(kwargs=kwargs, countdown=5)
        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    @freeze_time(datetime.fromtimestamp(1483500000))
    @patch('fitbit.Fitbit.subscription')
    def test_get_token_expired(self, subscription):
        subs_url = 'https://api.fitbit.com/1/user/-/apiSubscriptions.json'
        self.fbuser.expires_at = 1483400000
        self.fbuser.save()
        sub = {
            'ownerId': self.fbuser.fitbit_user,
            'subscriberId': '1',
            'subscriptionId': str(self.user.id),
            'collectionType': 'user',
            'ownerType': 'user'
        }
        subs = {'apiSubscriptions': [sub]}
        tok = {
            'access_token': 'fake_return_access_token',
            'refresh_token': 'fake_return_refresh_token',
            'expires_at': 1483600000,
        }
        with requests_mock.mock() as m:
            m.get(subs_url, text=json.dumps(subs), status_code=200)
            m.post('https://api.fitbit.com/oauth2/token', text=json.dumps(tok))

            response = self._get()

        mock_requests = m.request_history
        assert mock_requests[0].path == '/oauth2/token'
        assert mock_requests[0].headers['Authorization'] == _basic_auth_str(
            settings.FITAPP_CONSUMER_KEY,
            settings.FITAPP_CONSUMER_SECRET
        )
        assert mock_requests[1].path == '/1/user/-/apisubscriptions.json'
        assert mock_requests[1].headers['Authorization'] == 'Bearer {}'.format(
            tok['access_token']
        )
        subscription.assert_called_once_with(
            sub['subscriptionId'], sub['subscriberId'], method="DELETE")

    def test_unauthenticated(self):
        """User must be logged in to access Logout view."""
        self.client.logout()
        response = self._get()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserFitbit.objects.count(), 1)

    def test_unintegrated(self):
        """No Fitbit credentials required to access Logout view."""
        self.fbuser.delete()
        response = self._get()
        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    @patch('fitapp.tasks.unsubscribe.apply_async')
    def test_next(self, apply_async):
        """Logout view should redirect to GET['next'] if available."""
        response = self._get(get_kwargs={'next': '/test'})
        kwargs = self.fbuser.get_user_data()
        del kwargs['refresh_cb']
        apply_async.assert_called_with(kwargs=kwargs, countdown=5)
        self.assertRedirectsNoFollow(response, '/test')
        self.assertEqual(UserFitbit.objects.count(), 0)


class TestSubscription(FitappTestBase):
    @patch('fitbit.Fitbit.subscription')
    def test_subscribe(self, subscription):
        subscribe.apply_async((self.fbuser.fitbit_user, 1,))
        subscription.assert_called_once_with(self.user.id, 1, )

    @patch('fitbit.Fitbit.subscription')
    def test_subscribe_error(self, subscription):
        subscription.side_effect = HTTPConflict
        apply_result = subscribe.apply_async((self.fbuser.fitbit_user, 1,))
        self.assertEqual(apply_result.status, 'REJECTED')
        subscription.assert_called_once_with(self.user.id, 1, )

    @patch('fitbit.Fitbit.subscription')
    @patch('fitbit.Fitbit.list_subscriptions')
    def test_unsubscribe(self, list_subscriptions, subscription):
        sub = {
            'ownerId': self.fbuser.fitbit_user,
            'subscriberId': '1',
            'subscriptionId': str(self.user.id).encode('utf8'),
            'collectionType': 'user',
            'ownerType': 'user'
        }
        list_subscriptions.return_value = {'apiSubscriptions': [sub]}
        kwargs = self.fbuser.get_user_data()
        del kwargs['refresh_cb']
        unsubscribe.apply_async(kwargs=kwargs)
        list_subscriptions.assert_called_once_with()
        subscription.assert_called_once_with(
            sub['subscriptionId'], sub['subscriberId'], method="DELETE")

    @patch('fitbit.Fitbit.subscription')
    @patch('fitbit.Fitbit.list_subscriptions')
    def test_unsubscribe_error(self, list_subscriptions, subscription):
        list_subscriptions.side_effect = HTTPConflict
        kwargs = self.fbuser.get_user_data()
        del kwargs['refresh_cb']
        result = unsubscribe.apply_async(kwargs=kwargs)
        self.assertEqual(result.status, 'REJECTED')
        list_subscriptions.assert_called_once_with()
        self.assertEqual(subscription.call_count, 0)
