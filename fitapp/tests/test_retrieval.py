import json
from mock import patch

from django.core.urlresolvers import reverse

from fitbit import exceptions as fitbit_exceptions
from fitbit.api import Fitbit

from fitapp import utils
from fitapp.models import UserFitbit

from .base import FitappTestBase


class TestRetrievalUtility(FitappTestBase):
    """Tests for the get_fitbit_steps utility function."""

    @patch.object(Fitbit, 'time_series')
    def _mock_time_series(self, time_series=None, error=None, response=None):
        if error:
            time_series.side_effect = error('')
        elif response:
            time_series.return_value = response
        return utils.get_fitbit_steps(self.fbuser, '30d')

    def _error_test(self, error):
        with self.assertRaises(error) as c:
            self._mock_time_series(error=error)

    def test_value_error(self):
        """ValueError from the Fitbit.time_series should propagate."""
        self._error_test(ValueError)

    def test_unauthorized(self):
        """HTTPUnauthorized from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPUnauthorized)

    def test_forbidden(self):
        """HTTPForbidden from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPForbidden)

    def test_not_found(self):
        """HTTPNotFound from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPNotFound)

    def test_conflict(self):
        """HTTPConflict from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPConflict)

    def test_server_error(self):
        """HTTPServerError from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPServerError)

    def test_bad_request(self):
        """HTTPBadRequest from the Fitbit.time_series should propagate."""
        self._error_test(fitbit_exceptions.HTTPBadRequest)

    def test_retrieval(self):
        """get_fitbit_steps should return a list of daily steps data."""
        response = {'activities-steps': [1,2,3]}
        steps = self._mock_time_series(response=response)
        self.assertEquals(steps, response['activities-steps'])


class TestRetrievalView(FitappTestBase):
    """Tests for the get_steps view."""
    url_name = 'fitbit-steps'
    valid_periods = utils.get_valid_periods()

    def setUp(self):
        super(TestRetrievalView, self).setUp()
        self.period = '30d'

    def _get(self, period=None, **kwargs):
        period = period or self.period
        url_kwargs = {'period': period}
        url_kwargs.update(kwargs.get('url_kwargs', {}))
        return super(TestRetrievalView, self)._get(url_kwargs=url_kwargs,
                **kwargs)

    def _check_response(self, response, code, objects=None, error_msg=None):
        objects = objects or []
        self.assertEquals(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEquals(data['meta']['status_code'], code, error_msg)
        self.assertEquals(data['meta']['total_count'], len(objects),
                error_msg)
        self.assertEquals(data['objects'], objects, error_msg)

    def test_not_authenticated(self):
        """Status code should be 101 when user isn't logged in."""
        self.client.logout()
        response = self._get()
        self._check_response(response, 101)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_not_active(self):
        """Status code should be 101 when user isn't active."""
        self.user.is_active = False
        self.user.save()
        response = self._get()
        self._check_response(response, 101)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_not_integrated(self):
        """Status code should be 102 when user is not integrated."""
        self.fbuser.delete()
        response = self._get()
        self._check_response(response, 102)
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_invalid_credentials_unauthorized(self):
        """
        Status code should be 103 & credentials should be deleted when user
        integration is invalid.
        """
        response = self._mock_utility(error=fitbit_exceptions.HTTPUnauthorized)
        self._check_response(response, 103)
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_invalid_credentials_forbidden(self):
        """
        Status code should be 103 & credentials should be deleted when user
        integration is invalid.
        """
        response = self._mock_utility(error=fitbit_exceptions.HTTPForbidden)
        self._check_response(response, 103)
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_bad_period(self):
        """Status code should be 104 when invalid period is given."""
        self.period = 'bad'
        response = self._get()
        self._check_response(response, 104)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_rate_limited(self):
        """Status code should be 105 when Fitbit rate limit is hit."""
        response = self._mock_utility(error=fitbit_exceptions.HTTPConflict)
        self._check_response(response, 105)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_fitbit_error(self):
        """Status code should be 106 when Fitbit server error occurs."""
        response = self._mock_utility(error=fitbit_exceptions.HTTPServerError)
        self._check_response(response, 106)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_get(self):
        """View should return JSON steps data."""
        steps = [{'dateTime': '2000-01-01', 'value': 10}]
        for period in self.valid_periods:
            self.period = period
            response = self._mock_utility(response=steps)
            error_msg = 'Should be able to retrieve data for {0}.'.format(
                    self.period)
            self._check_response(response, 100, steps, error_msg)
            self.assertEquals(UserFitbit.objects.count(), 1)

    def test_405(self):
        """View should not respond to anything but a GET request."""
        url = reverse('fitbit-steps', kwargs={'period': self.period})
        for method in (self.client.post, self.client.head,
                self.client.options, self.client.put, self.client.delete):
            response = method(url)
            self.assertEquals(response.status_code, 405)
