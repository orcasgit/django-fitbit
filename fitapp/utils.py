from django.conf import settings

from fitbit import Fitbit

from .models import UserFitbit


def create_fitbit(consumer_key=None, consumer_secret=None, **kwargs):
    """Shortcut to create a Fitbit instance.

    If consumer_key or consumer_secret are not provided, then the values
    specified in settings are used.
    """
    if consumer_key is None:
        consumer_key = getattr(settings, 'FITBIT_CONSUMER_KEY', None)
    if consumer_secret is None:
        consumer_secret = getattr(settings, 'FITBIT_CONSUMER_SECRET', None)
    return Fitbit(consumer_key=consumer_key, consumer_secret=consumer_secret,
            **kwargs)


def is_integrated(user):
    """Returns True if we have Oauth info for the user.

    This does not currently require that the token and secret are valid.
    """
    return UserFitbit.objects.filter(user=user).exists()


def get_fitbit_steps(fbuser, period):
    """Creates a Fitbit API instance and retrieves step data for the period.

    Several exceptions may be thrown:
        ValueError       - Invalid period argument.
        HTTPUnauthorized - 401 - fbuser has bad authentication credentials.
        HTTPForbidden    - 403 - This isn't specified by Fitbit, but does
                                 appear in the Python Fitbit library.
        HTTPNotFound     - 404 - The specific resource doesn't exist.
        HTTPConflict     - 409 - Usually a rate limit issue.
        HTTPServerError  - >=500 - Fitbit server error or maintenance.
        HTTPBadRequest   - >=400 - Bad request.
    """
    fb = create_fitbit(**fbuser.get_user_data())
    data = None
    data = fb.time_series('activities/steps', period=period)
    key = 'activities-steps'
    steps = data[key] if data and key in data else None
    return steps
