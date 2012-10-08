import json
from mock import patch

from fitbit import exceptions as fitbit_exceptions
from fitbit.api import Fitbit

from fitapp import utils

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
        steps = self.mock_time_series(response=response)
        self.assertEquals(steps, response['activities-steps'])


class TestRetrievalView(FitappTestBase):
    """Tests for the get_steps view."""
    url_name = 'fitbit-steps'
    valid_periods = ['1d', '7d', '30d', '1w', '1m', '3m', '6m', '1y', 'max']

    def setUp(self):
        super(TestRetrievalView, self).setUp()
        self.period = '30d'

    def _get(self, period=None, **kwargs):
        period = period or self.period
        url_kwargs = {'period': period}
        url_kwargs.update(kwargs.get('url_kwargs', {}))
        return super(TestRetrievalView, self)._get(url_kwargs=url_kwargs,
                **kwargs)

    def test_not_authenticated(self):
        """View should return 404 when user isn't logged in."""
        self.client.logout()
        response = self._get()
        self.assertEquals(response.status_code, 404)

    def test_not_active(self):
        """View should return 404 when user isn't active."""
        self.user.is_active = False
        self.user.save()
        response = self._get()
        self.assertEquals(response.status_code, 404)

    def test_not_integrated(self):
        """View should return 401 when user is not integrated."""
        self.fbuser.delete()
        response = self._get()
        self.assertEquals(response.status_code, 401)

    def test_bad_fitbit_data(self):
        """View should return 403 when user integration is invalid."""
        response = self._mock_utility(error=fitbit_exceptions.HTTPUnauthorized)
        self.assertEquals(response.status_code, 403)

        response = self._mock_utility(error=fitbit_exceptions.HTTPForbidden)
        self.assertEquals(response.status_code, 403)

    def test_bad_period(self):
        """View should return 400 when invalid period is given."""
        self.period = 'bad'
        response = self._get()
        self.assertEquals(response.status_code, 400)

    def test_rate_limited(self):
        """View should return 409 when Fitbit rate limit is hit."""
        response = self._mock_utility(error=fitbit_exceptions.HTTPConflict)
        self.assertEquals(response.status_code, 409)

    def test_fitbit_error(self):
        """View should return 502 when Fitbit server error occurs."""
        response = self._mock_utility(error=fitbit_exceptions.HTTPServerError)
        self.assertEquals(response.status_code, 502)

    def test_retrieval(self):
        """View should return JSON steps data."""
        steps = [{'dateTime': '2000-01-01', 'value': 10}]
        for period in self.valid_periods:
            self.period = period
            response = self._mock_utility(response=steps)
            error_msg = 'Should be able to retrieve data for {0}.'.format(
                    self.period)
            self.assertEquals(response.status_code, 200, error_msg)
            self.assertEquals(response.content, json.dumps(steps), error_msg)
