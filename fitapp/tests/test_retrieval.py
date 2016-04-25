from __future__ import absolute_import

import celery
import json
import sys

from dateutil import parser
from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from freezegun import freeze_time
from mock import MagicMock, patch

from fitbit import exceptions as fitbit_exceptions
from fitbit.api import Fitbit

from fitapp import utils
from fitapp.models import UserFitbit, TimeSeriesData, TimeSeriesDataType
from fitapp.tasks import get_time_series_data

try:
    from io import BytesIO
except ImportError:  # Python 2.x fallback
    from StringIO import StringIO as BytesIO

from .base import FitappTestBase


class TestRetrievalUtility(FitappTestBase):
    """Tests for the get_fitbit_data utility function."""

    def setUp(self):
        super(TestRetrievalUtility, self).setUp()
        self.period = '30d'
        self.base_date = '2012-06-01'
        self.end_date = None

    @patch.object(Fitbit, 'time_series')
    def _mock_time_series(self, time_series=None, error=None, response=None,
                          error_attrs={}):
        if error:
            exc = error(self._error_response())
            for k, v in error_attrs.items():
                setattr(exc, k, v)
            time_series.side_effect = exc
        elif response:
            time_series.return_value = response
        resource_type = TimeSeriesDataType.objects.get(
            category=TimeSeriesDataType.activities, resource='steps')
        return utils.get_fitbit_data(
            self.fbuser, resource_type, base_date=self.base_date,
            period=self.period, end_date=self.end_date)

    def _error_test(self, error):
        with self.assertRaises(error):
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

    def test_too_many_requests(self):
        """HTTPTooManyRequests from the Fitbit.time_series should propagate."""
        try:
            self._mock_time_series(error=fitbit_exceptions.HTTPTooManyRequests,
                                   error_attrs={'retry_after_secs': 35})
        except fitbit_exceptions.HTTPTooManyRequests:
            self.assertEqual(sys.exc_info()[1].retry_after_secs, 35)
        else:
            assert False, 'Should have thrown exception'

    def test_retrieval(self):
        """get_fitbit_data should return a list of daily steps data."""
        response = {'activities-steps': [1, 2, 3]}
        steps = self._mock_time_series(response=response)
        self.assertEqual(steps, response['activities-steps'])


class TestRetrievalTask(FitappTestBase):
    def setUp(self):
        super(TestRetrievalTask, self).setUp()
        self.category = 'activities'
        self.date = '2013-05-02'
        self.value = 10

    def _receive_fitbit_updates(self, file=False):
        d = json.dumps([{
            'subscriptionId': self.fbuser.user.id,
            'ownerId': self.fbuser.fitbit_user,
            'collectionType': self.category,
            'date': self.date
        }]).encode('utf8')
        kwargs = {'data': d, 'content_type': 'application/json'}
        if file:
            updates_stringio = BytesIO(d)
            updates = InMemoryUploadedFile(
                updates_stringio, None, 'updates', 'text', len(d), None)
            kwargs = {'data': {'updates': updates}}
        res = self.client.post(reverse('fitbit-update'), **kwargs)
        assert res.status_code, 204

    @patch('fitapp.utils.get_fitbit_data')
    def test_subscription_update(self, get_fitbit_data):
        # Check that celery tasks get made when a notification is received
        # from Fitbit.
        get_fitbit_data.return_value = [{'value': self.value}]
        category = getattr(TimeSeriesDataType, self.category)
        self._receive_fitbit_updates()
        self.assertEqual(get_fitbit_data.call_count, 1)
        # Check that the cache lock has been deleted
        self.assertEqual(
            cache.get('fitapp.get_time_series_data-lock-%s-%s-%s' % (
                self.fbuser.fitbit_user, category, self.date)
            ), None)
        date = parser.parse(self.date)
        for tsd in TimeSeriesData.objects.filter(user=self.user, date=date):
            assert tsd.value, self.value

    @patch('fitapp.utils.get_fitbit_data')
    def test_subscription_update_file(self, get_fitbit_data):
        # Check that celery tasks get made when an updates file notification
        # is received from Fitbit.
        get_fitbit_data.return_value = [{'value': self.value}]
        category = getattr(TimeSeriesDataType, self.category)
        self._receive_fitbit_updates(file=True)
        self.assertEqual(get_fitbit_data.call_count, 1)
        # Check that the cache lock has been deleted
        self.assertEqual(
            cache.get('fitapp.get_time_series_data-lock-%s-%s-%s' % (
                self.fbuser.fitbit_user, category, self.date)
            ), None)
        date = parser.parse(self.date)
        for tsd in TimeSeriesData.objects.filter(user=self.user, date=date):
            assert tsd.value, self.value

    @patch('fitapp.utils.get_fitbit_data')
    @patch('django.core.cache.cache.add')
    def test_subscription_update_locked(self, mock_add, get_fitbit_data):
        # Check that celery tasks do not get made when a notification is
        # received from Fitbit, but there is already a matching task in
        # progress
        mock_add.return_value = False
        self.assertEqual(TimeSeriesData.objects.count(), 0)
        self._receive_fitbit_updates()
        self.assertEqual(get_fitbit_data.call_count, 0)
        self.assertEqual(TimeSeriesData.objects.count(), 0)

    @patch('fitapp.utils.get_fitbit_data')
    def test_subscription_update_too_many(self, get_fitbit_data):
        # Check that celery tasks get postponed if the rate limit is hit
        exc = fitbit_exceptions.HTTPTooManyRequests(self._error_response())
        exc.retry_after_secs = 21
        category = getattr(TimeSeriesDataType, self.category)

        def side_effect(*args, **kwargs):
            # Delete the cache lock after the first try and adjust the
            # get_fitbit_data mock to be successful
            lock_id = 'fitapp.tasks-lock-{0}-{1}-{2}'.format(
                self.fbuser.fitbit_user, category, self.date)
            cache.delete(lock_id)
            get_fitbit_data.side_effect = None
            get_fitbit_data.return_value = [{
                'dateTime': self.date,
                'value': '34'
            }]
            raise exc
        get_fitbit_data.side_effect = side_effect
        self.assertEqual(TimeSeriesData.objects.count(), 0)
        result = get_time_series_data.apply_async(
            (self.fbuser.fitbit_user,),
            {'categories': [category], 'date': parser.parse(self.date)})
        result.get()
        # Since celery is in eager mode, we expect a Retry exception first
        # and then task executions for each resource in the category to be
        # successful
        self.assertEqual(get_fitbit_data.call_count, 24)
        self.assertEqual(TimeSeriesData.objects.count(), 23)
        self.assertEqual(TimeSeriesData.objects.all()[0].value, '34')

    def test_problem_queueing_task(self):
        get_time_series_data = MagicMock()
        # If queueing the task raises an exception, it doesn't propagate
        get_time_series_data.apply_async.side_effect = Exception
        try:
            self._receive_fitbit_updates()
        except:
            assert False, 'Any errors should be captured in the view'


class RetrievalViewTestBase(object):
    """Base methods for the get_steps view."""
    url_name = 'fitbit-steps'
    valid_periods = utils.get_valid_periods()

    def setUp(self):
        super(RetrievalViewTestBase, self).setUp()
        self.period = '30d'
        self.base_date = '2012-06-06'
        self.end_date = '2012-07-07'

    def _check_response(self, response, code, objects=None, error_msg=None):
        objects = objects or []
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode('utf8'))
        self.assertEqual(data['meta']['status_code'], code, error_msg)
        self.assertEqual(data['meta']['total_count'], len(objects), error_msg)
        self.assertEqual(data['objects'], objects, error_msg)

    def test_not_authenticated(self):
        """Status code should be 101 when user isn't logged in."""
        self.client.logout()
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 101)
        self.assertEqual(UserFitbit.objects.count(), 1)

    def test_not_active(self):
        """Status code should be 101 when user isn't active."""
        self.user.is_active = False
        self.user.save()
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 101)
        self.assertEqual(UserFitbit.objects.count(), 1)

    @override_settings(FITAPP_SUBSCRIBE=False)
    def test_not_integrated(self):
        """
        Status code should be 102 when an unsubscribed user is not integrated.
        """
        self.fbuser.delete()
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 102)
        self.assertEqual(UserFitbit.objects.count(), 0)

    @override_settings(FITAPP_SUBSCRIBE=False)
    def test_invalid_credentials_unauthorized(self):
        """
        Status code should be 103 & credentials should be deleted when user
        integration is invalid.
        """
        response = self._mock_utility(get_kwargs=self._data(),
                                      error=fitbit_exceptions.HTTPUnauthorized)
        self._check_response(response, 103)
        self.assertEqual(UserFitbit.objects.count(), 0)

    @override_settings(FITAPP_SUBSCRIBE=False)
    def test_invalid_credentials_forbidden(self):
        """
        Status code should be 103 & credentials should be deleted when user
        integration is invalid.
        """
        response = self._mock_utility(get_kwargs=self._data(),
                                      error=fitbit_exceptions.HTTPForbidden)
        self._check_response(response, 103)
        self.assertEqual(UserFitbit.objects.count(), 0)

    @override_settings(FITAPP_SUBSCRIBE=False)
    def test_rate_limited(self):
        """Status code should be 105 when Fitbit rate limit is hit."""
        response = self._mock_utility(get_kwargs=self._data(),
                                      error=fitbit_exceptions.HTTPConflict)
        self._check_response(response, 105)

    @override_settings(FITAPP_SUBSCRIBE=False)
    def test_fitbit_error(self):
        """Status code should be 106 when Fitbit server error occurs."""
        response = self._mock_utility(get_kwargs=self._data(),
                                      error=fitbit_exceptions.HTTPServerError)
        self._check_response(response, 106)

    def test_405(self):
        """View should not respond to anything but a GET request."""
        url = reverse('fitbit-data', args=['activities', 'steps'])
        for method in (self.client.post, self.client.head,
                       self.client.options, self.client.put,
                       self.client.delete):
            response = method(url)
            self.assertEqual(response.status_code, 405)

    def test_ambiguous(self):
        """Status code should be 104 when both period & end_date are given."""
        data = {'end_date': self.end_date, 'period': self.period,
                'base_date': self.base_date}
        response = self._get(get_kwargs=data)
        self._check_response(response, 104)


class TestRetrievePeriod(RetrievalViewTestBase, FitappTestBase):

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

    @freeze_time('2012-06-06')
    def test_no_base_date(self):
        """Base date should be optional for period request."""
        data = self._data()
        data.pop('base_date')
        steps = [{'dateTime': '2012-06-07', 'value': '10'}]
        TimeSeriesData.objects.create(
            user=self.user,
            resource_type=TimeSeriesDataType.objects.get(
                category=TimeSeriesDataType.activities, resource='steps'),
            date=steps[0]['dateTime'],
            value=steps[0]['value']
        )
        response = self._mock_utility(response=steps, get_kwargs=data)
        self._check_response(response, 100, steps)

    def test_bad_base_date(self):
        """Status code should be 104 when invalid base date is given."""
        self.base_date = 'bad'
        response = self._get(get_kwargs=self._data())
        self._check_response(response, 104)

    def test_period(self):
        steps = [{'dateTime': '2012-06-07', 'value': '10'}]
        TimeSeriesData.objects.create(
            user=self.user,
            resource_type=TimeSeriesDataType.objects.get(
                category=TimeSeriesDataType.activities, resource='steps'),
            date=steps[0]['dateTime'],
            value=steps[0]['value']
        )
        for period in self.valid_periods:
            self.period = period
            data = self._data()
            response = self._mock_utility(response=steps, get_kwargs=data)
            error_msg = 'Should be able to retrieve data for {0}.'.format(
                self.period)
            self._check_response(response, 100, steps, error_msg)

    def test_period_not_integrated(self):
        """
        Period data is returned to a subscribed user who is not integrated
        """
        self.fbuser.delete()
        steps = [{'dateTime': '2012-06-07', 'value': '10'}]
        TimeSeriesData.objects.create(
            user=self.user,
            resource_type=TimeSeriesDataType.objects.get(
                category=TimeSeriesDataType.activities, resource='steps'),
            date=steps[0]['dateTime'],
            value=steps[0]['value']
        )
        for period in self.valid_periods:
            self.period = period
            data = self._data()
            response = self._mock_utility(response=steps, get_kwargs=data)
            error_msg = 'Should be able to retrieve data for {0}.'.format(
                self.period)
            self._check_response(response, 100, steps, error_msg)


class TestRetrieveRange(RetrievalViewTestBase, FitappTestBase):

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
        steps = [{'dateTime': '2012-06-07', 'value': '10'}]
        TimeSeriesData.objects.create(
            user=self.user,
            resource_type=TimeSeriesDataType.objects.get(
                category=TimeSeriesDataType.activities, resource='steps'),
            date=steps[0]['dateTime'],
            value=steps[0]['value']
        )

        response = self._mock_utility(response=steps,
                                      get_kwargs=self._data())
        self._check_response(response, 100, steps)

    def test_range_not_integrated(self):
        """
        Range data is returned to a subscribed user who is not integrated
        """
        self.fbuser.delete()
        steps = [{'dateTime': '2012-06-07', 'value': '10'}]
        TimeSeriesData.objects.create(
            user=self.user,
            resource_type=TimeSeriesDataType.objects.get(
                category=TimeSeriesDataType.activities, resource='steps'),
            date=steps[0]['dateTime'],
            value=steps[0]['value']
        )

        response = self._mock_utility(response=steps,
                                      get_kwargs=self._data())
        self._check_response(response, 100, steps)
