import logging
import random

from celery import shared_task
from celery.exceptions import Ignore, Reject
from dateutil import parser
from django.core.cache import cache
from django.db import transaction
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
        except Exception as e:
            logger.exception("Error subscribing user: %s" % e)
            raise Reject(e, requeue=False)


@shared_task
def unsubscribe(*args, **kwargs):
    """ Unsubscribe from a user's fitbit data """

    fb = utils.create_fitbit(**kwargs)
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

    # Create a lock so we don't try to run the same task multiple times
    sdat = date.strftime('%Y-%m-%d') if date else 'ALL'
    lock_id = '{0}-lock-{1}-{2}-{3}'.format(__name__, fitbit_user, _type, sdat)
    if not cache.add(lock_id, 'true', LOCK_EXPIRE):
        logger.debug('Already retrieving %s data for date %s, user %s' % (
            _type, fitbit_user, sdat))
        raise Ignore()

    try:
        with transaction.atomic():
            # Block until we have exclusive update access to this UserFitbit, so
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
