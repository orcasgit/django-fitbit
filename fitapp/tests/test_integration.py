from django.core.urlresolvers import reverse

from fitapp import utils
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


class TestFitbitView(FitappTestBase):
    url_name = 'fitbit'

    def test_get(self):
        """Should be able to retrieve Fitbit page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)

    def test_unintegrated(self):
        """Fitbit credentials are not necessary to access Fitbit page."""
        self.fbuser.delete()
        response = self._get()
        self.assertEquals(response.status_code, 200)

    def test_unauthenticated(self):
        """User must be logged in to access Fitbit view."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)

    def test_next(self):
        """Fitbit view should store GET['next'] in session['fitbit_next']."""
        response = self._get(get_kwargs={'next': 'hello'})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(self.client.session['fitbit_next'], 'hello')


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
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_unauthenticated(self):
        """User must be logged in to access Login view."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_unintegrated(self):
        """Fitbit credentials not required to access Login view."""
        self.fbuser.delete()
        fbuser = self.create_userfitbit(user=self.user)
        response = self._mock_client()
        self.assertRedirectsNoFollow(response, '/test')
        self.assertTrue('token' in self.client.session)
        self.assertEquals(UserFitbit.objects.count(), 1)


class TestCompleteView(FitappTestBase):
    url_name = 'fitbit-complete'
    key = 'abc'
    secret = '123'
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

    def _mock_client(self, **kwargs):
        defaults = {
            'key': self.key,
            'secret': self.secret,
            'user_id': self.user_id,
        }
        defaults.update(kwargs)
        return super(TestCompleteView, self)._mock_client(**defaults)

    def test_get(self):
        """Complete view should fetch & store user's access credentials."""
        response = self._mock_client()
        self.assertRedirectsNoFollow(response, reverse('fitbit'))
        fbuser = UserFitbit.objects.get()
        self.assertEquals(fbuser.user, self.user)
        self.assertEquals(fbuser.auth_token, self.key)
        self.assertEquals(fbuser.auth_secret, self.secret)
        self.assertEquals(fbuser.fitbit_user, self.user_id)

    def test_unauthenticated(self):
        """User must be logged in to access Complete view."""
        self.client.logout()
        response = self._mock_client()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_next(self):
        """
        Complete view should redirect to session['fitbit_next'] if available.
        """
        self._set_session_vars(fitbit_next='/test')
        response = self._mock_client()
        self.assertRedirectsNoFollow(response, '/test')
        fbuser = UserFitbit.objects.get()
        self.assertEquals(fbuser.user, self.user)
        self.assertEquals(fbuser.auth_token, self.key)
        self.assertEquals(fbuser.auth_secret, self.secret)
        self.assertEquals(fbuser.fitbit_user, self.user_id)

    def test_access_error(self):
        """
        Complete view should redirect to error if access token is
        inaccessible.
        """
        response = self._mock_client(error=Exception)
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_no_token(self):
        """Complete view should redirect to error if token isn't in session."""
        response = self._get(use_token=False)
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_no_verifier(self):
        """
        Complete view should redirect to error if verifier param is not
        present.
        """
        response = self._get(use_verifier=False)
        self.assertRedirectsNoFollow(response, reverse('fitbit-error'))
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_integrated(self):
        """
        Complete view should overwrite existing credentials for this user.
        """
        self.fbuser = self.create_userfitbit(user=self.user)
        response = self._mock_client()
        fbuser = UserFitbit.objects.get()
        self.assertEquals(fbuser.user, self.user)
        self.assertEquals(fbuser.auth_token, self.key)
        self.assertEquals(fbuser.auth_secret, self.secret)
        self.assertEquals(fbuser.fitbit_user, self.user_id)
        self.assertRedirectsNoFollow(response, reverse('fitbit'))


class TestErrorView(FitappTestBase):
    url_name = 'fitbit-error'

    def test_get(self):
        """Should be able to retrieve Error page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)

    def test_unauthenticated(self):
        """User must be logged in to access Error view."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)

    def test_unintegrated(self):
        """No Fitbit credentials required to access Error view."""
        self.fbuser.delete()
        response = self._get()
        self.assertEquals(response.status_code, 200)


class TestLogoutView(FitappTestBase):
    url_name = 'fitbit-logout'

    def test_get(self):
        """Logout view should remove associated UserFitbit and redirect."""
        response = self._get()
        self.assertRedirectsNoFollow(response, reverse('fitbit'))
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_unauthenticated(self):
        """User must be logged in to access Logout view."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_unintegrated(self):
        """No Fitbit credentials required to access Logout view."""
        self.fbuser.delete()
        response = self._get()
        self.assertRedirectsNoFollow(response, reverse('fitbit'))
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_next(self):
        """Logout view should redirect to GET['next'] if available."""
        response = self._get(get_kwargs={'next': '/test'})
        self.assertRedirectsNoFollow(response, '/test')
        self.assertEquals(UserFitbit.objects.count(), 0)
