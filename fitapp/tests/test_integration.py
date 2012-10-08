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

    def test_other_user_is_integrated(self):
        """utils.is_integrated can be called on any user."""
        user2 = self.create_user()
        fbuser2 = self.create_userfitbit(user=user2)
        self.assertTrue(utils.is_integrated(user2))

    def test_other_user_is_not_integrated(self):
        """utils.is_integrated can be called on any user."""
        user2 = self.create_user()
        self.assertFalse(utils.is_integrated(user2))


class TestFitbitView(FitappTestBase):
    url_name = 'fitbit'

    def test_get(self):
        """Should be able to retrieve Fitbit page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)

    def test_unauthenticated(self):
        """User must be logged in to see Fitbit page."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)

    def test_next(self):
        """Fitbit view should store GET['next'] in session['fitbit_next']."""
        response = self._get(next='hello')
        self.assertEquals(response.status_code, 200)
        self.assertEquals(self.client.session['fitbit_next'], 'hello')


class TestLoginView(FitappTestBase):
    url_name = 'fitbit-login'

    def test_get(self):
        """
        Login view should generate & store a request token then
        redirect to an authorization URL.
        """
        response = self.mock_client()
        self.assert_correct_redirect(response, 'test')
        self.assertTrue('token' in self.client.session)

    def test_unauthenticated(self):
        """User must be logged in to see Login page."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)


class TestCompleteView(FitappTestBase):
    url_name = 'fitbit-complete'

    def setUp(self):
        super(TestCompleteView, self).setUp()
        self.fbuser.delete()
        self.key = 'abc'
        self.secret = '123'
        self.user_id = 'hello'

    def _set_session_vars(self, **kwargs):
        session = self.client.session
        for key, value in kwargs.items():
            session[key] = value
        try:
            session.save()
        except AttributeError:
            pass

    def _get(self, url_name=None, use_token=True, use_verifier=True, **kwargs):
        if use_token:
            self._set_session_vars(token='token')
        if use_verifier:
            kwargs.update({'oauth_verifier': 'hello'})
        return super(TestCompleteView, self)._get(url_name, **kwargs)

    def mock_client(self, **kwargs):
        defaults = {
            'key': self.key,
            'secret': self.secret,
            'user_id': self.user_id,
        }
        defaults.update(kwargs)
        return super(TestCompleteView, self).mock_client(**defaults)

    # *****
    def test_get(self):
        """TODO"""
        response = self.mock_client()
        fbuser = UserFitbit.objects.get()
        self.assertEquals(fbuser.user, self.user)
        self.assertEquals(fbuser.auth_token, self.key)
        self.assertEquals(fbuser.auth_secret, self.secret)
        self.assertEquals(fbuser.fitbit_user, self.user_id)
        self.assert_correct_redirect(response, 'fitbit')

    def test_unauthenticated(self):
        """User must be logged in to see Fitbit error page."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_next(self):
        """TODO"""
        self._set_session_vars(fitbit_next=reverse('test'))
        response = self.mock_client()
        fbuser = UserFitbit.objects.get()
        self.assertEquals(fbuser.user, self.user)
        self.assertEquals(fbuser.auth_token, self.key)
        self.assertEquals(fbuser.auth_secret, self.secret)
        self.assertEquals(fbuser.fitbit_user, self.user_id)
        self.assert_correct_redirect(response, 'test')

    def test_error(self):
        """
        Fitbit Complete view should redirect to error if access token is
        inaccessible.
        """
        response = self.mock_client(error=Exception)
        self.assert_correct_redirect(response, 'fitbit-error')
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_no_token(self):
        """
        Fitbit Complete view should redirect to error if token isn't in
        session.
        """
        response = self._get(use_token=False)
        self.assert_correct_redirect(response, 'fitbit-error')
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_no_verifier(self):
        """
        Fitbit Complete view should redirect to error if verifier param is not
        present.
        """
        response = self._get(use_verifier=False)
        self.assert_correct_redirect(response, 'fitbit-error')
        self.assertEquals(UserFitbit.objects.count(), 0)


class TestErrorView(FitappTestBase):
    url_name = 'fitbit-error'

    # *****
    def test_get(self):
        """Should be able to retrieve Error page."""
        response = self._get()
        self.assertEquals(response.status_code, 200)

    def test_unauthenticated(self):
        """User must be logged in to see Error page."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)


class TestLogoutView(FitappTestBase):
    url_name = 'fitbit-logout'

    def test_get(self):
        """Logout view should remove associated UserFitbit and redirect."""
        response = self._get()
        self.assert_correct_redirect(response, 'fitbit')
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_unauthenticated(self):
        """User must be logged in to seee Logout page."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_next(self):
        """Logout view should redirect to GET['next'] if available."""
        response = self._get(next=reverse('test'))
        self.assert_correct_redirect(response, 'test')
        self.assertEquals(UserFitbit.objects.count(), 0)

