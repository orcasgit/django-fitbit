import logging
import random
import sys
import datetime
import time

from celery import shared_task
from celery.exceptions import Ignore, Reject
from dateutil import parser
from django.core.cache import cache
from django.db import transaction
from django.utils.timezone import utc
from fitbit.exceptions import HTTPBadRequest, HTTPTooManyRequests

from . import utils
from .models import TimeSeriesData, TimeSeriesDataType, UserFitbit

logger = logging.getLogger(__name__)
LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes


@shared_task
def subscribe(fitbit_user, subscriber_id):
    """ Subscribe to the user's fitbit data """

    fbusers = UserFitbit.objects.filter(fitbit_user=fitbit_user)
    for fbuser in fbusers:
        fb = utils.create_fitbit(**fbuser.get_user_data())
        try:
            fb.subscription(fbuser.user.id, subscriber_id)
        except Exception as e:
            logger.exception("Error subscribing user: %s" % e)
            raise Reject(e, requeue=False)


@shared_task
def unsubscribe(*args, **kwargs):
    """ Unsubscribe from a user's fitbit data """

    # Ignore updated token, it's not needed. The session gets the new token
    # automatically
    fb = utils.create_fitbit(refresh_cb=lambda token: None, **kwargs)
    try:
        for sub in fb.list_subscriptions()['apiSubscriptions']:
            if sub['ownerId'] == kwargs['user_id']:
                fb.subscription(sub['subscriptionId'], sub['subscriberId'],
                                method="DELETE")
    except Exception as e:
        logger.exception("Error unsubscribing user: %s" % e)
        raise Reject(e, requeue=False)


@shared_task(bind=True)
def get_time_series_data(self, fitbit_user, cat, resource, date=None):
    """ Get the user's time series data """

    try:
        _type = TimeSeriesDataType.objects.get(category=cat, resource=resource)
    except TimeSeriesDataType.DoesNotExist as e:
        logger.exception("The resource %s in category %s doesn't exist" % (
            resource, cat))
        raise Reject(e, requeue=False)

    # # Create a lock so we don't try to run the same task multiple times
    # sdat = date.strftime('%Y-%m-%d') if date else 'ALL'
    # lock_id = '{0}-lock-{1}-{2}-{3}'.format(__name__, fitbit_user, _type, sdat)
    # if not cache.add(lock_id, 'true', LOCK_EXPIRE):
    #     logger.debug('Already retrieving %s data for date %s, user %s' % (
    #         _type, fitbit_user, sdat))
    #     raise Ignore()

    try:
        with transaction.atomic():
            # Block until we have exclusive up date access to this UserFitbit, so
            # that another process cannot step on us when we update tokens
            fbusers = UserFitbit.objects.select_for_update().filter(
                fitbit_user=fitbit_user)
            dates = {'base_date': 'today', 'period': 'max'}
            if date:
                dates = {'base_date': date, 'end_date': date}

            for fbuser in fbusers:
                data = utils.get_fitbit_data(fbuser, _type, **dates)
                for datum in data:
                    # Create new record or update existing record
                    date = parser.parse(datum['dateTime'])
                    tsd, created = TimeSeriesData.objects.get_or_create(
                        user=fbuser.user, resource_type=_type, date=date)
                    tsd.value = datum['value']
                    tsd.save()
            # Release the lock
            cache.delete(lock_id)
    except HTTPTooManyRequests as e:
        # We have hit the rate limit for the user, retry when it's reset,
        # according to the reply from the failing API call
        countdown = e.retry_after_secs + int(
            # Add exponential back-off + random jitter
            random.uniform(2, 4) ** self.request.retries
        )
        logger.debug('Rate limit reached, will try again in {} seconds'.format(
            countdown))
        raise get_time_series_data.retry(exc=e, countdown=countdown)
    except HTTPBadRequest as e:
        # If the resource is elevation or floors, we are just getting this
        # error because the data doesn't exist for this user, so we can ignore
        # the error
        if not ('elevation' in resource or 'floors' in resource):
            logger.exception("Exception updating data: ".format(e))
            raise Reject(e, requeue=False)
    except Exception as e:
        logger.exception("Exception updating data: %s" % e)
        raise Reject(e, requeue=False)


@shared_task(bind=True)
def get_intraday_data(self, fitbit_user, cat, resource, date, tz_offset, start_time=None, end_time=None):
    """
    Get the user's intraday data for a specified date, convert to UTC prior to
    saving.

    The Fitbit API stipulates that intraday data can only be retrieved for one
    day at a time.
    """
    try:
        _type = TimeSeriesDataType.objects.get(category=cat, resource=resource)
    except TimeSeriesDataType.DoesNotExist:
        logger.exception("The resource %s in category %s doesn't exist" %
                         (resource, cat))
        raise Reject(sys.exc_info()[1], requeue=False)
    if not _type.intraday_support:
        logger.exception("The resource %s in category %s does not support "
                         "intraday time series" % (resource, cat))
        raise Reject(sys.exc_info()[1], requeue=False)

    # Create a lock so we don't try to run the same task multiple times
    # sdat = date.strftime('%Y-%m-%d')

    fbusers = UserFitbit.objects.filter(fitbit_user=fitbit_user)
    dates = {'base_date': date, 'period': '1d'}
    try:
        with transaction.atomic():
            for fbuser in fbusers:
                data = utils.get_fitbit_data(fbuser, _type, start_time=start_time,
                                             end_time=end_time,
                                             **dates)
                resource_path = _type.path().replace('/', '-')
                key = resource_path + "-intraday"
                if data[key]['datasetType'] != 'minute':
                    logger.exception("The resource returned is not "
                                     "minute-level data")
                    raise Reject(sys.exc_info()[1], requeue=False)
                intraday = data[key]['dataset']
                logger.info("Date for intraday task: {}".format(date))
                for minute in intraday:
                    date_time = parser.parse(date[:10] + ' ' + minute['time'])
                    utc_datetime = date_time + datetime.timedelta(hours=tz_offset)
                    utc_datetime = utc_datetime.replace(tzinfo=utc)
                    value = minute['value']
                    # Don't create unnecessary records
                    if not utils.get_setting('FITAPP_SAVE_INTRADAY_ZERO_VALUES'):
                        if int(float(value)) == 0:
                            continue
                    # Create new record or update existing
                    tsd, created = TimeSeriesData.objects.get_or_create(
                        user=fbuser.user, resource_type=_type, date=utc_datetime,
                        intraday=True)
                    tsd.value = value
                    tsd.save()
            # Release the lock
    except HTTPTooManyRequests:
        # We have hit the rate limit for the user, retry when it's reset,
        # according to the reply from the failing API call
        e = sys.exc_info()[1]
        logger.debug('Rate limit reached for user %s, will try again in %s seconds' %
                     (fitbit_user, e.retry_after_secs))
        raise get_intraday_data.retry(exc=e, countdown=e.retry_after_secs)
    except HTTPBadRequest:
        # If the resource is elevation or floors, we are just getting this
        # error because the data doesn't exist for this user, so we can ignore
        # the error
        if not ('elevation' in resource or 'floors' in resource):
            exc = sys.exc_info()[1]
            logger.exception("Exception updating intraday data for user %s: %s" % (fitbit_user, exc))
            raise Reject(exc, requeue=False)
    except Exception:
        exc = sys.exc_info()[1]
        logger.exception("Exception updating data for user %s: %s" % (fitbit_user, exc))
        raise Reject(exc, requeue=False)
