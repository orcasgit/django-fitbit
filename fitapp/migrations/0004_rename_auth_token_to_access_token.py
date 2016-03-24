# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('fitapp', '0003_add_refresh_token_field'),
    ]

    operations = [
        migrations.RenameField(
            model_name='userfitbit',
            old_name='auth_token',
            new_name='access_token',
        ),
    ]
