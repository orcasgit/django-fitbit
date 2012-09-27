from django.conf import settings

from fitbit import Fitbit

from fitapp.models import UserFitbit


def create_fitbit():
    fb = Fitbit(consumer_key=settings.FITBIT_CONSUMER_KEY,
            consumer_secret=settings.FITBIT_SECRET_KEY)
    return fb


def is_integrated(user):
    """Returns True if we have an Oauth token and secret for the user.

    This does not currently require that the token and secret are valid.
    """
    if not user.is_authenticated():
        return False
    try:
        fbuser = UserFitbit.objects.get(user=user)
    except UserFitbit.DoesNotExist:
        return False
    return fbuser.auth_token and fbuser.auth_secret
