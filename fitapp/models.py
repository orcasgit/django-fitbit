from django.contrib.auth.models import User
from django.db import models


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
    value = models.CharField(null=True, default=None, max_length=32)

    class Meta:
        unique_together = ('user', 'resource_type', 'date')

    def string_date(self):
        return self.date.strftime('%Y-%m-%d')
