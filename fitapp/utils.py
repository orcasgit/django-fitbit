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
