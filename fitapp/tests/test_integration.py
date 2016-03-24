from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.http import HttpRequest
from fitbit.exceptions import HTTPConflict
from mock import patch

from fitapp import utils
from fitapp.decorators import fitbit_integration_warning
from fitapp.models import UserFitbit, TimeSeriesDataType
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
        apply_async.assert_called_once_with(kwargs=self.fbuser.get_user_data(),
                                            countdown=5)
        self.assertRedirectsNoFollow(
            response, utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        self.assertEqual(UserFitbit.objects.count(), 0)

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
        apply_async.assert_called_with(kwargs=self.fbuser.get_user_data(),
                                       countdown=5)
        self.assertRedirectsNoFollow(response, '/test')
        self.assertEqual(UserFitbit.objects.count(), 0)


class TestSubscription(FitappTestBase):
    @patch('fitbit.Fitbit.subscription')
    def test_subscribe(self, subscription):
        subscribe.apply_async((self.fbuser.fitbit_user, 1,))
        subscription.assert_called_once_with(self.user.id, 1,)

    @patch('fitbit.Fitbit.subscription')
    def test_subscribe_error(self, subscription):
        subscription.side_effect = HTTPConflict
        apply_result = subscribe.apply_async((self.fbuser.fitbit_user, 1,))
        self.assertEqual(apply_result.status, 'REJECTED')
        subscription.assert_called_once_with(self.user.id, 1,)

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
        unsubscribe.apply_async(kwargs=self.fbuser.get_user_data())
        list_subscriptions.assert_called_once_with()
        subscription.assert_called_once_with(
            sub['subscriptionId'], sub['subscriberId'], method="DELETE")

    @patch('fitbit.Fitbit.subscription')
    @patch('fitbit.Fitbit.list_subscriptions')
    def test_unsubscribe_error(self, list_subscriptions, subscription):
        list_subscriptions.side_effect = HTTPConflict
        result = unsubscribe.apply_async(kwargs=self.fbuser.get_user_data())
        self.assertEqual(result.status, 'REJECTED')
        list_subscriptions.assert_called_once_with()
        self.assertEqual(subscription.call_count, 0)
