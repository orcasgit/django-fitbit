# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('fitapp', '0005_upgrade_oauth1_tokens_to_oauth2'),
    ]

    operations = [
        migrations.AlterField(
            model_name='timeseriesdata',
            name='date',
            field=models.DateField(help_text=b'The date the data was recorded'),
        ),
        migrations.AlterField(
            model_name='timeseriesdata',
            name='resource_type',
            field=models.ForeignKey(help_text=b'The type of time series data', to='fitapp.TimeSeriesDataType'),
        ),
        migrations.AlterField(
            model_name='timeseriesdata',
            name='user',
            field=models.ForeignKey(help_text=b"The data's user", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='timeseriesdata',
            name='value',
            field=models.CharField(default=None, max_length=32, null=True, help_text=b'The value of the data. This is typically a number, though saved as a string here. The units can be inferred from the data type. For example, for step data the value might be "9783" (the units) would be "steps"'),
        ),
        migrations.AlterField(
            model_name='timeseriesdatatype',
            name='category',
            field=models.IntegerField(help_text=b'The category of the time series data, one of: 0(foods), 1(activities), 2(sleep), 3(body)', choices=[(0, b'foods'), (1, b'activities'), (2, b'sleep'), (3, b'body')]),
        ),
        migrations.AlterField(
            model_name='timeseriesdatatype',
            name='resource',
            field=models.CharField(help_text=b'The specific time series resource. This is the string that will be used for the [resource-path] of the API url referred to in the Fitbit documentation', max_length=128),
        ),
        migrations.AlterField(
            model_name='userfitbit',
            name='access_token',
            field=models.TextField(help_text=b'The OAuth2 access token'),
        ),
        migrations.AlterField(
            model_name='userfitbit',
            name='auth_secret',
            field=models.TextField(help_text=b'The OAuth2 auth secret'),
        ),
        migrations.AlterField(
            model_name='userfitbit',
            name='fitbit_user',
            field=models.CharField(help_text=b'The fitbit user ID', unique=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='userfitbit',
            name='refresh_token',
            field=models.TextField(help_text=b'The OAuth2 refresh token'),
        ),
        migrations.AlterField(
            model_name='userfitbit',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL, help_text=b'The user'),
        ),
    ]
