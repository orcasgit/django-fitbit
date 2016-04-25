import logging
import sys

from celery import shared_task
from celery.exceptions import Ignore, Reject
from dateutil import parser
from django.core.cache import cache
from fitbit.exceptions import HTTPBadRequest, HTTPTooManyRequests

from . import utils
from .models import UserFitbit, TimeSeriesData, TimeSeriesDataType


logger = logging.getLogger(__name__)
LOCK_EXPIRE = 60 * 5 # Lock expires in 5 minutes


@shared_task
def subscribe(fitbit_user, subscriber_id):
    """ Subscribe to the user's fitbit data """

    fbusers = UserFitbit.objects.filter(fitbit_user=fitbit_user)
    for fbuser in fbusers:
        fb = utils.create_fitbit(**fbuser.get_user_data())
        try:
            fb.subscription(fbuser.user.id, subscriber_id)
        except:
            exc = sys.exc_info()[1]
            logger.exception("Error subscribing user: %s" % exc)
            raise Reject(exc, requeue=False)


@shared_task
def unsubscribe(*args, **kwargs):
    """ Unsubscribe from a user's fitbit data """

    fb = utils.create_fitbit(**kwargs)
    try:
        for sub in fb.list_subscriptions()['apiSubscriptions']:
            if sub['ownerId'] == kwargs['user_id']:
                fb.subscription(sub['subscriptionId'], sub['subscriberId'],
                                method="DELETE")
    except:
        exc = sys.exc_info()[1]
        logger.exception("Error unsubscribing user: %s" % exc)
        raise Reject(exc, requeue=False)


@shared_task
def get_time_series_data(fitbit_user, categories=[], date=None):
    """ Get the user's time series data """

    filters = {'category__in': categories} if categories else {}
    types = TimeSeriesDataType.objects.filter(**filters)
    if not types.exists():
        logger.exception("Couldn't find the time series data types")
        raise Reject(sys.exc_info()[1], requeue=False)

    # Create a lock so we don't try to run the same task multiple times
    sdat = date.strftime('%Y-%m-%d') if date else 'ALL'
    cats = '-'.join('%s' % i for i in categories)
    lock_id = '{0}-lock-{1}-{2}-{3}'.format(__name__, fitbit_user, cats, sdat)
    if not cache.add(lock_id, 'true', LOCK_EXPIRE):
        logger.debug('Already working on %s' % lock_id)
        raise Ignore()

    fbusers = UserFitbit.objects.filter(fitbit_user=fitbit_user)
    dates = {'base_date': 'today', 'period': 'max'}
    if date:
        dates = {'base_date': date, 'end_date': date}
    try:
        for fbuser in fbusers:
            for _type in types:
                data = utils.get_fitbit_data(fbuser, _type, **dates)
                for datum in data:
                    # Create new record or update existing record
                    date = parser.parse(datum['dateTime'])
                    tsd, created = TimeSeriesData.objects.get_or_create(
                        user=fbuser.user, resource_type=_type, date=date)
                    tsd.value = datum['value']
                    tsd.save()
    except HTTPTooManyRequests:
        # We have hit the rate limit for the user, retry when it's reset,
        # according to the reply from the failing API call
        e = sys.exc_info()[1]
        logger.debug('Rate limit reached, will try again in %s seconds' %
                     e.retry_after_secs)
        raise get_time_series_data.retry(exc=e, countdown=e.retry_after_secs)
    except HTTPBadRequest:
        # If the resource is elevation or floors, we are just getting this
        # error because the data doesn't exist for this user, so we can ignore
        # the error
        if not ('elevation' in _type.resource or 'floors' in _type.resource):
            exc = sys.exc_info()[1]
            logger.exception("Exception updating data: %s" % exc)
            raise Reject(exc, requeue=False)
    except Exception:
        exc = sys.exc_info()[1]
        logger.exception("Exception updating data: %s" % exc)
        raise Reject(exc, requeue=False)
    finally:
        # Release the lock
        cache.delete(lock_id)
