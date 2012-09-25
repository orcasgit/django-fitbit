from fitbit import Fitbit

from django.conf import settings


def create_fitbit():
    fb = Fitbit(consumer_key=settings.FITBIT_CONSUMER_KEY,
            consumer_secret=settings.FITBIT_SECRET_KEY)
    return fb
