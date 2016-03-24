from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


UserModel = getattr(settings, 'AUTH_USER_MODEL', 'auth.User')


@python_2_unicode_compatible
class UserFitbit(models.Model):
    user = models.OneToOneField(UserModel)
    fitbit_user = models.CharField(max_length=32, unique=True)
    access_token = models.TextField()
    auth_secret = models.TextField()
    refresh_token = models.TextField()

    def __str__(self):
        return self.user.__str__()

    def get_user_data(self):
        return {
            'user_id': self.fitbit_user,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token
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

    def __str__(self):
        return self.path()

    class Meta:
        unique_together = ('category', 'resource',)
        ordering = ['category', 'resource']

    def path(self):
        return '/'.join([self.get_category_display(), self.resource])


class TimeSeriesData(models.Model):
    """
    The purpose of this model is to store Fitbit user data obtained from their
    time series API (https://wiki.fitbit.com/display/API/API-Get-Time-Series).
    """

    user = models.ForeignKey(UserModel)
    resource_type = models.ForeignKey(TimeSeriesDataType)
    date = models.DateField()
    value = models.CharField(null=True, default=None, max_length=32)

    class Meta:
        unique_together = ('user', 'resource_type', 'date')

    def string_date(self):
        return self.date.strftime('%Y-%m-%d')
