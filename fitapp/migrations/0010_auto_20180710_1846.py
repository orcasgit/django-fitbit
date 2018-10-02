# Generated by Django 2.0.6 on 2018-07-10 18:46

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    UserModel = getattr(settings, 'FITAPP_USER_MODEL', 'auth.User')
    dependencies = [
        migrations.swappable_dependency(UserModel),
        ('fitapp', '0009_auto_20180110_1605'),
    ]

    operations = [
        migrations.AddField(
            model_name='timeseriesdata',
            name='intraday',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='timeseriesdata',
            name='date',
            field=models.DateTimeField(help_text='The date the data was recorded, and time if intraday.'),
        ),
        migrations.AlterUniqueTogether(
            name='timeseriesdata',
            unique_together={('user', 'resource_type', 'date', 'intraday')},
        ),
    ]
