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
