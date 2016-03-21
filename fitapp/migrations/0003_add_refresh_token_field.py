# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitapp', '0002_initial_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='userfitbit',
            name='refresh_token',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
    ]
