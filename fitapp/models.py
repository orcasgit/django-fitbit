from django.conf import settings
from django.contrib.auth.models import User
from django.db import models

from itertools import chain


class UserFitbit(models.Model):
    user = models.OneToOneField(User)
    fitbit_user = models.CharField(max_length=32)
    auth_token = models.TextField()
    auth_secret = models.TextField()

    def __unicode__(self):
        return self.user.__unicode__()

    def get_user_data(self):
        return {
            'user_key': self.auth_token,
            'user_secret': self.auth_secret,
            'user_id': self.fitbit_user,
        }


class Unit(models.Model):
    """
    This model is intended to store Fitbit's data about unit systems, which
    can be found here: https://wiki.fitbit.com/display/API/API+Unit+System
    """

    LOCALE_CHOICES = (
        (0, 'en_US'),
        (1, 'en_GB'),
        (2, 'METRIC'),
    )
    UNIT_TYPE_CHOICES = (
        (0, 'duration'),
        (1, 'distance'),
        (2, 'elevation'),
        (3, 'height'),
        (4, 'weight'),
        (5, 'measurements'),
        (6, 'liquids'),
        (7, 'blood glucose'),
    )
    UNIT_NAME_CHOICES = (
        (0, 'millisecond'),
        (1, 'mile'),
        (2, 'foot'),
        (3, 'inch'),
        (4, 'pound'),
        (5, 'fl oz'),
        (6, 'mg/dL'),
        (7, 'kilometer'),
        (8, 'meter'),
        (9, 'centimeter'),
        (10, 'stone'),
        (11, 'milliliter'),
        (12, 'mmol/l'),
    )
    locale = models.IntegerField(choices=LOCALE_CHOICES)
    unit_type = models.IntegerField(choices=UNIT_TYPE_CHOICES)
    unit_name = models.IntegerField(choices=UNIT_NAME_CHOICES)

    class Meta:
        unique_together = ('locale', 'unit_type',)


class TimeSeriesDataType(models.Model):
    """
    This model is intended to store information about Fitbit's time series
    resources, which can be found here:
    https://wiki.fitbit.com/display/API/API-Get-Time-Series
    """

    foods = 0
    activities = 1
    sleep = 2
    body = 3
    CATEGORY_CHOICES = (
        (foods, 'foods'),
        (activities, 'activities'),
        (sleep, 'sleep'),
        (body, 'body'),
    )
    category = models.IntegerField(choices=CATEGORY_CHOICES)
    resource = models.CharField(max_length=128)
    unit_type = models.IntegerField(choices=Unit.UNIT_TYPE_CHOICES, null=True)

    class Meta:
        unique_together = ('category', 'resource',)

    def path(self):
        return '/'.join([self.get_category_display(), self.resource])


class TimeSeriesData(models.Model):
    """
    The purpose of this model is to store Fitbit user data obtained from their
    time series API (https://wiki.fitbit.com/display/API/API-Get-Time-Series).
    """

    user = models.ForeignKey(User)
    resource_type = models.ForeignKey(TimeSeriesDataType)
    date = models.DateField()
    value = models.FloatField(null=True, default=None)
    dirty = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'resource_type', 'date')
