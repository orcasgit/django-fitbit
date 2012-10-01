from django.conf import settings

from fitbit import Fitbit

from fitapp.models import UserFitbit


def create_fitbit(**kwargs):
    data = {
        'consumer_key': settings.FITBIT_CONSUMER_KEY,
        'consumer_secret': settings.FITBIT_CONSUMER_SECRET,
    }
    data.update(kwargs)
    return Fitbit(**data)


def is_integrated(user):
    """Returns True if we have Oauth info for the user.

    This does not currently require that the token and secret are valid.
    """
    if not user.is_authenticated():
        return False
    try:
        fbuser = UserFitbit.objects.get(user=user)
    except UserFitbit.DoesNotExist:
        return False
    return True
