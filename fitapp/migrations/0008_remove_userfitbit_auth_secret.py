# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitapp', '0007_userfitbit_expires_at'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userfitbit',
            name='auth_secret',
        ),
    ]
