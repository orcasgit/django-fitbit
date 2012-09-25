from django.contrib.auth.models import User
from django.db import models


class UserFitbit(models.Model):
    user = models.ForeignKey(User)
    fitbit_user = models.CharField(max_length=32)
    auth_token = models.TextField(null=True, blank=True)
    auth_secret = models.TextField(null=True, blank=True)

    def __unicode__(self):
        return self.user.__unicode__()
