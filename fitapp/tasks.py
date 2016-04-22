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
LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes


def _hit_rate_limit(exc, task):
    # We have hit the rate limit for the user, retry when it's reset,
    # according to the reply from the failing API call
    logger.debug('Rate limit reached, will try again in %s seconds' %
                 exc.retry_after_secs)
    raise task.retry(exc=exc, countdown=exc.retry_after_secs)


def _generic_task_exception(exc, task_name):
    logger.exception("Exception running task %s: %s" % (task_name, exc))
    raise Reject(exc, requeue=False)


@shared_task
def subscribe(fitbit_user, subscriber_id):
    """ Subscribe the user and retrieve historical data for it """
    update_user_timezone.apply_async((fitbit_user,), countdown=1)
    for fbuser in UserFitbit.objects.filter(fitbit_user=fitbit_user):
        fb = utils.create_fitbit(**fbuser.get_user_data())
        try:
            fb.subscription(fbuser.user.id, subscriber_id)
        except HTTPTooManyRequests:
            _hit_rate_limit(sys.exc_info()[1], subscribe)
        except Exception:
            _generic_task_exception(sys.exc_info()[1], 'subscribe')

    # Create tasks for all data in all data types
    for i, _type in enumerate(TimeSeriesDataType.objects.all()):
        # Delay execution for a few seconds to speed up response Offset each
        # call by 5 seconds so they don't bog down the server
        get_time_series_data.apply_async(
            (fitbit_user, _type.category, _type.resource,),
            countdown=10 + (i * 5))


@shared_task
def unsubscribe(*args, **kwargs):
    """ Unsubscribe from a user's fitbit data """

    fb = utils.create_fitbit(**kwargs)
    try:
        for sub in fb.list_subscriptions()['apiSubscriptions']:
            if sub['ownerId'] == kwargs['user_id']:
                fb.subscription(sub['subscriptionId'], sub['subscriberId'],
                                method="DELETE")
    except HTTPTooManyRequests:
        _hit_rate_limit(sys.exc_info()[1], unsubscribe)
    except Exception:
        _generic_task_exception(sys.exc_info()[1], 'unsubscribe')


@shared_task
def get_time_series_data(fitbit_user, cat, resource, date=None):
    """ Get the user's time series data """

    try:
        _type = TimeSeriesDataType.objects.get(category=cat, resource=resource)
    except TimeSeriesDataType.DoesNotExist:
        logger.exception("The resource %s in category %s doesn't exist" % (
            resource, cat))
        raise Reject(sys.exc_info()[1], requeue=False)

    # Create a lock so we don't try to run the same task multiple times
    sdat = date.strftime('%Y-%m-%d') if date else 'ALL'
    lock_id = '{0}-lock-{1}-{2}-{3}'.format(__name__, fitbit_user, _type, sdat)
    if not cache.add(lock_id, 'true', LOCK_EXPIRE):
        logger.debug('Already retrieving %s data for date %s, user %s' % (
            _type, fitbit_user, sdat))
        raise Ignore()

    fbusers = UserFitbit.objects.filter(fitbit_user=fitbit_user)
    dates = {'base_date': 'today', 'period': 'max'}
    if date:
        dates = {'base_date': date, 'end_date': date}
    try:
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
    except HTTPTooManyRequests:
        _hit_rate_limit(sys.exc_info()[1], get_time_series_data)
    except HTTPBadRequest:
        # If the resource is elevation or floors, we are just getting this
        # error because the data doesn't exist for this user, so we can ignore
        # the error
        if not ('elevation' in resource or 'floors' in resource):
            exc = sys.exc_info()[1]
            logger.exception("Exception updating data: %s" % exc)
            raise Reject(exc, requeue=False)
    except Exception:
        _generic_task_exception(sys.exc_info()[1], 'get_time_series_data')


@shared_task
def update_user_timezone(fitbit_user):
    """ Get the user's profile and update the timezone we have on file """

    fbusers = UserFitbit.objects.filter(fitbit_user=fitbit_user)
    try:
        for fbuser in fbusers:
            fb = utils.create_fitbit(**fbuser.get_user_data())
            profile = fb.user_profile_get()
            fbuser.timezone = profile['user']['timezone']
            fbuser.save()
            utils.check_for_new_token(fbuser, fb.client.token)
    except HTTPTooManyRequests:
        _hit_rate_limit(sys.exc_info()[1], update_user_timezone)
    except Exception:
        _generic_task_exception(sys.exc_info()[1], 'update_user_timezone')
