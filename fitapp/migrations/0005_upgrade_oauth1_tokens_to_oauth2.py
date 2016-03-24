from django.db import migrations, models

from fitbit.api import FitbitOauth2Client
from fitapp.utils import get_setting
from oauthlib.oauth2.rfc6749.errors import MissingTokenError


def forwards(apps, schema_editor):
    UserFitbit = apps.get_model('fitapp', 'UserFitbit')
    for fbuser in UserFitbit.objects.filter(refresh_token=''):
        try:
            token = FitbitOauth2Client(
                get_setting('FITAPP_CONSUMER_KEY'),
                get_setting('FITAPP_CONSUMER_SECRET'),
                refresh_token='{0}:{1}'.format(
                    fbuser.access_token, fbuser.auth_secret)
            ).refresh_token()
            fbuser.access_token = token['access_token']
            fbuser.refresh_token = token['refresh_token']
            fbuser.save()
        except MissingTokenError:
            # Delete fitbit user if existing access_token is invalid
            fbuser.delete()


def backwards(apps, schema_editor):
    # Don't do anything since OAuth1 is no longer supported by Fitbit
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('fitapp', '0004_rename_auth_token_to_access_token'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
