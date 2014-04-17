import mock

from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.http import HttpRequest

from fitapp import utils
from fitapp.decorators import fitbit_integration_warning
from fitapp.models import UserFitbit

from .base import FitappTestBase


class TestIntegrationUtility(FitappTestBase):

    def test_is_integrated(self):
        """Users with stored OAuth information are integrated."""
        self.assertTrue(utils.is_integrated(self.user))

    def test_is_not_integrated(self):
        """User is not integrated if we have no OAuth data for them."""
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

        with mock.patch.object(messages, 'error', mock_error) as error:
            return fitbit_integration_warning(msg=msg)(self.fake_view)(
                    self.fake_request)

    def test_unauthenticated(self):
        """Message should be added if user is not logged in."""
        self.fake_request.user = AnonymousUser()
        results = self._mock_decorator()

        self.assertEqual(results, "hello")
        self.assertEqual(len(self.messages), 1)
        self.assertEqual(self.messages[0],
                utils.get_setting('FITAPP_DECORATOR_MESSAGE'))

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
        self.assertEqual(self.messages[0],
                utils.get_setting('FITAPP_DECORATOR_MESSAGE'))

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
        Login view should generate & store a request token then
        redirect to an authorization URL.
        """
        response = self._mock_client()
        self.assertRedirectsNoFollow(response, '/test')
        self.assertTrue('token' in self.client.session)
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
        self.assertRedirectsNoFollow(response, '/test')
        self.assertTrue('token' in self.client.session)
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_next(self):
        response = self._mock_client(get_kwargs={'next': '/next'})
        self.assertRedirectsNoFollow(response, '/test')
        self.assertEqual(self.client.session.get('fitbit_next', None),
                '/next')
        self.assertEqual(UserFitbit.objects.count(), 1)


class TestCompleteView(FitappTestBase):
    url_name = 'fitbit-complete'
    resource_owner_key = 'abc'
    resource_owner_secret = '123'
    user_id = 'userid'

    def setUp(self):
        super(TestCompleteView, self).setUp()
        self.fbuser.delete()

    def _get(self, use_token=True, use_verifier=True, **kwargs):
        if use_token:
            self._set_session_vars(token='token')
        get_kwargs = kwargs.pop('get_kwargs', {})
        if use_verifier:
            get_kwargs.update({'oauth_verifier': 'hello'})
        return super(TestCompleteView, self)._get(get_kwargs=get_kwargs,
                **kwargs)

    def _mock_client(self, client_kwargs=None, **kwargs):
        client_kwargs = client_kwargs or {}
        defaults = {
            'resource_owner_key': self.resource_owner_key,
            'resource_owner_secret': self.resource_owner_secret,
            'user_id': self.user_id,
        }
        defaults.update(client_kwargs)
        return super(TestCompleteView, self)._mock_client(
                client_kwargs=defaults, **kwargs)

    def test_get(self):
        """Complete view should fetch & store user's access credentials."""
        response = self._mock_client()
        self.assertRedirectsNoFollow(response,
                utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        fbuser = UserFitbit.objects.get()
        self.assertEqual(fbuser.user, self.user)
        self.assertEqual(fbuser.auth_token, self.resource_owner_key)
        self.assertEqual(fbuser.auth_secret, self.resource_owner_secret)
        self.assertEqual(fbuser.fitbit_user, self.user_id)

    def test_unauthenticated(self):
        """User must be logged in to access Complete view."""
        self.client.logout()
        response = self._mock_client()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_next(self):
        """
        Complete view should redirect to session['fitbit_next'] if available.
        """
        self._set_session_vars(fitbit_next='/test')
        response = self._mock_client()
        self.assertRedirectsNoFollow(response, '/test')
        fbuser = UserFitbit.objects.get()
        self.assertEqual(fbuser.user, self.user)
        self.assertEqual(fbuser.auth_token, self.resource_owner_key)
        self.assertEqual(fbuser.auth_secret, self.resource_owner_secret)
        self.assertEqual(fbuser.fitbit_user, self.user_id)

    def test_access_error(self):
        """
        Complete view should redirect to error if access token is
        inaccessible.
        """
        response = self._mock_client(client_kwargs={'error': Exception})
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_no_token(self):
        """Complete view should redirect to error if token isn't in session."""
        response = self._get(use_token=False)
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_no_verifier(self):
        """
        Complete view should redirect to error if verifier param is not
        present.
        """
        response = self._get(use_verifier=False)
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_integrated(self):
        """
        Complete view should overwrite existing credentials for this user.
        """
        self.fbuser = self.create_userfitbit(user=self.user)
        response = self._mock_client()
        fbuser = UserFitbit.objects.get()
        self.assertEqual(fbuser.user, self.user)
        self.assertEqual(fbuser.auth_token, self.resource_owner_key)
        self.assertEqual(fbuser.auth_secret, self.resource_owner_secret)
        self.assertEqual(fbuser.fitbit_user, self.user_id)
        self.assertRedirectsNoFollow(response,
                utils.get_setting('FITAPP_LOGIN_REDIRECT'))


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

    def test_get(self):
        """Logout view should remove associated UserFitbit and redirect."""
        response = self._get()
        self.assertRedirectsNoFollow(response,
                utils.get_setting('FITAPP_LOGIN_REDIRECT'))
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
        self.assertRedirectsNoFollow(response,
                utils.get_setting('FITAPP_LOGIN_REDIRECT'))
        self.assertEqual(UserFitbit.objects.count(), 0)

    def test_next(self):
        """Logout view should redirect to GET['next'] if available."""
        response = self._get(get_kwargs={'next': '/test'})
        self.assertRedirectsNoFollow(response, '/test')
        self.assertEqual(UserFitbit.objects.count(), 0)
