# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitapp', '0005_upgrade_oauth1_tokens_to_oauth2'),
    ]

    operations = [
        migrations.AddField(
            model_name='userfitbit',
            name='expires_at',
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='userfitbit',
            name='timezone',
            field=models.CharField(default='UTC', max_length=128),
            preserve_default=False,
        ),
    ]
