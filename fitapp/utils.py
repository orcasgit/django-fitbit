import pytz

from datetime import datetime
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils.timezone import localtime, make_aware

from fitbit import Fitbit

from . import defaults, models


def create_fitbit(consumer_key=None, consumer_secret=None, **kwargs):
    """Shortcut to create a Fitbit instance.

    If consumer_key or consumer_secret are not provided, then the values
    specified in settings are used.
    """
    if consumer_key is None:
        consumer_key = get_setting('FITAPP_CONSUMER_KEY')
    if consumer_secret is None:
        consumer_secret = get_setting('FITAPP_CONSUMER_SECRET')

    if consumer_key is None or consumer_secret is None:
        raise ImproperlyConfigured(
            "Consumer key and consumer secret cannot "
            "be null, and must be explicitly specified or set in your "
            "Django settings"
        )

    return Fitbit(consumer_key, consumer_secret, **kwargs)


def is_integrated(user):
    """Returns ``True`` if we have Oauth info for the user.

    This does not require that the token and secret are valid.

    :param user: A Django User.
    """
    if user.is_authenticated() and user.is_active:
        return models.UserFitbit.objects.filter(user=user).exists()
    return False


def get_valid_periods():
    """Returns list of periods for which one may request time series data."""
    return ['1d', '7d', '30d', '1w', '1m', '3m', '6m', '1y', 'max']


@transaction.atomic()
def get_fitbit_data(fbuser, resource_type, base_date=None, period=None,
                    end_date=None):
    """Creates a Fitbit API instance and retrieves step data for the period.

    Several exceptions may be thrown:
        TypeError           - Either end_date or period must be specified, but
                              not both.
        ValueError          - Invalid argument formats.
        HTTPUnauthorized    - 401 - fbuser has bad authentication credentials.
        HTTPForbidden       - 403 - This isn't specified by Fitbit, but does
                                 appear in the Python Fitbit library.
        HTTPNotFound        - 404 - The specific resource doesn't exist.
        HTTPConflict        - 409 - HTTP conflict
        HTTPTooManyRequests - 429 - Hitting the rate limit
        HTTPServerError     - >=500 - Fitbit server error or maintenance.
        HTTPBadRequest      - >=400 - Bad request.
    """
    fb = create_fitbit(**fbuser.get_user_data())
    resource_path = resource_type.path()
    data = fb.time_series(resource_path, user_id=fbuser.fitbit_user,
                          period=period, base_date=base_date,
                          end_date=end_date)

    check_for_new_token(fbuser, fb.client.token)
    return data[resource_path.replace('/', '-')]


def check_for_new_token(fbuser, token):
    """
    Update the token if necessary. We are making sure we have a valid
    access_token and refresh_token next time we request Fitbit data
    """
    expires_at = token.get('expires_at', None)
    if expires_at and expires_at > fbuser.expires_at:
        # We've compared the expires_at float values sent by fitbit, now let's
        # check that the timezone aware expires_at datetime is greater than now
        # in the fitbit user's timezone
        timezone = pytz.timezone(fbuser.timezone)
        expires_at_local = make_aware(datetime.fromtimestamp(expires_at),
                                      timezone)
        utc_now = make_aware(datetime.utcnow(), pytz.timezone('UTC'))
        if expires_at_local > localtime(utc_now, timezone):
            fbuser.access_token = token['access_token']
            fbuser.refresh_token = token['refresh_token']
            fbuser.expires_at = expires_at
            fbuser.save()
            from .tasks import update_user_timezone
            update_user_timezone.apply_async(
                (fbuser.fitbit_user,), countdown=1)


def get_setting(name, use_defaults=True):
    """Retrieves the specified setting from the settings file.

    If the setting is not found and use_defaults is True, then the default
    value specified in defaults.py is used. Otherwise, we raise an
    ImproperlyConfigured exception for the setting.
    """
    if hasattr(settings, name):
        return getattr(settings, name)
    if use_defaults:
        if hasattr(defaults, name):
            return getattr(defaults, name)
    msg = "{0} must be specified in your settings".format(name)
    raise ImproperlyConfigured(msg)
