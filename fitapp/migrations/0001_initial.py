# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TimeSeriesData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateField()),
                ('value', models.CharField(default=None, max_length=32, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TimeSeriesDataType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('category', models.IntegerField(choices=[(0, b'foods'), (1, b'activities'), (2, b'sleep'), (3, b'body')])),
                ('resource', models.CharField(max_length=128)),
            ],
            options={
                'ordering': ['category', 'resource'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserFitbit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('fitbit_user', models.CharField(unique=True, max_length=32)),
                ('auth_token', models.TextField()),
                ('auth_secret', models.TextField()),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='timeseriesdatatype',
            unique_together=set([('category', 'resource')]),
        ),
        migrations.AddField(
            model_name='timeseriesdata',
            name='resource_type',
            field=models.ForeignKey(to='fitapp.TimeSeriesDataType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='timeseriesdata',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='timeseriesdata',
            unique_together=set([('user', 'resource_type', 'date')]),
        ),
    ]
