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

    def setUp(self):
        super(TestRetrievalUtility, self).setUp()
        self.period = '30d'
        self.base_date = '2012-06-01'
        self.end_date = None

    @patch.object(Fitbit, 'time_series')
    def _mock_time_series(self, time_series=None, error=None, response=None):
        if error:
            time_series.side_effect = error('')
        elif response:
            time_series.return_value = response
        return utils.get_fitbit_steps(self.fbuser, base_date=self.base_date,
                period=self.period, end_date=self.end_date)

    def _error_test(self, error):
        with self.assertRaises(error) as c:
            self._mock_time_series(error=error)

    def test_value_error(self):
        """ValueError from the Fitbit.time_series should propagate."""
        self._error_test(ValueError)

    def test_type_error(self):
        """TypeError from the Fitbit.time_series should propagate."""
        self._error_test(TypeError)

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


class TestRetrievalViewBase(object):
    """Base methods for the get_steps view."""
    url_name = 'fitbit-steps'
    valid_periods = utils.get_valid_periods()

    def setUp(self):
        super(TestRetrievalViewBase, self).setUp()
        self.period = '30d'
        self.base_date = '2012-06-06'
        self.end_date = '2012-07-07'

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
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 101)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_not_active(self):
        """Status code should be 101 when user isn't active."""
        self.user.is_active = False
        self.user.save()
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 101)
        self.assertEquals(UserFitbit.objects.count(), 1)

    def test_not_integrated(self):
        """Status code should be 102 when user is not integrated."""
        self.fbuser.delete()
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 102)
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_invalid_credentials_unauthorized(self):
        """
        Status code should be 103 & credentials should be deleted when user
        integration is invalid.
        """
        response = self._mock_utility(get_kwargs=self._data(),
                error=fitbit_exceptions.HTTPUnauthorized)
        self._check_response(response, 103)
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_invalid_credentials_forbidden(self):
        """
        Status code should be 103 & credentials should be deleted when user
        integration is invalid.
        """
        response = self._mock_utility(get_kwargs=self._data(),
                error=fitbit_exceptions.HTTPForbidden)
        self._check_response(response, 103)
        self.assertEquals(UserFitbit.objects.count(), 0)

    def test_rate_limited(self):
        """Status code should be 105 when Fitbit rate limit is hit."""
        response = self._mock_utility(get_kwargs=self._data(),
                error=fitbit_exceptions.HTTPConflict)
        self._check_response(response, 105)

    def test_fitbit_error(self):
        """Status code should be 106 when Fitbit server error occurs."""
        response = self._mock_utility(get_kwargs=self._data(),
                error=fitbit_exceptions.HTTPServerError)
        self._check_response(response, 106)

    def test_405(self):
        """View should not respond to anything but a GET request."""
        url = reverse('fitbit-steps')
        for method in (self.client.post, self.client.head,
                self.client.options, self.client.put, self.client.delete):
            response = method(url)
            self.assertEquals(response.status_code, 405)

    def test_ambiguous(self):
        """Status code should be 104 when both period & end_date are given."""
        data = {'end_date': self.end_date, 'period': self.period,
                'base_date': self.base_date}
        response = self._get(get_kwargs=data)
        self._check_response(response, 104)


class TestRetrievePeriod(TestRetrievalViewBase, FitappTestBase):

    def _data(self):
        return {'base_date': self.base_date, 'period': self.period}

    def test_no_period(self):
        """Status code should be 104 when no period is given."""
        data = self._data()
        data.pop('period')
        response = self._get(get_kwargs=data)
        self._check_response(response, 104)

    def test_bad_period(self):
        """Status code should be 104 when invalid period is given."""
        self.period = 'bad'
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 104)

    def test_no_base_date(self):
        """Base date should be optional for period request."""
        data = self._data()
        data.pop('base_date')
        steps = [{'dateTime': '2000-01-01', 'value': 10}]
        response = self._mock_utility(response=steps, get_kwargs=data)
        self._check_response(response, 100, steps)

    def test_bad_base_date(self):
        """Status code should be 104 when invalid base date is given."""
        self.base_date = 'bad'
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 104)

    def test_period(self):
        steps = [{'dateTime': '2000-01-01', 'value': 10}]
        for period in self.valid_periods:
            self.period = period
            data = self._data()
            response = self._mock_utility(response=steps, get_kwargs=data)
            error_msg = 'Should be able to retrieve data for {0}.'.format(
                    self.period)
            self._check_response(response, 100, steps, error_msg)


class TestRetrieveRange(TestRetrievalViewBase, FitappTestBase):

    def _data(self):
        return {'base_date': self.base_date, 'end_date': self.end_date}

    def test_range__no_base_date(self):
        """Status code should be 104 when no base date is given."""
        data = self._data()
        data.pop('base_date')
        response = self._get(get_kwargs=data)
        self._check_response(response, 104)

    def test_range__bad_base_date(self):
        """Status code should be 104 when invalid base date is given."""
        self.base_date = 'bad'
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 104)

    def test_range__no_end_date(self):
        """Status code should be 104 when no end date is given."""
        data = self._data()
        data.pop('end_date')
        response = self._get(get_kwargs=data)
        self._check_response(response, 104)

    def test_range__bad_end_date(self):
        """Status code should be 104 when invalid end date is given."""
        self.end_date = 'bad'
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 104)

    def test_range(self):
        steps = [{'dateTime': '2000-01-01', 'value': 10}]
        response = self._mock_utility(response=steps,
                get_kwargs = self._data())
        self._check_response(response, 100, steps)
