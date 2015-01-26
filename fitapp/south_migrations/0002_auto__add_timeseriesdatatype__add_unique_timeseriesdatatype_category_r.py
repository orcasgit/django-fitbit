# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


# Safe User import for Django < 1.5
try:
    from django.contrib.auth import get_user_model
except ImportError:
    from django.contrib.auth.models import User
else:
    User = get_user_model()

# With the default User model these will be 'auth.User' and 'auth.user'
# so instead of using orm['auth.User'] we can use orm[user_orm_label]
user_orm_label = '%s.%s' % (User._meta.app_label, User._meta.object_name)
user_model_label = '%s.%s' % (User._meta.app_label, User._meta.module_name)


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TimeSeriesDataType'
        db.create_table('fitapp_timeseriesdatatype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.IntegerField')()),
            ('resource', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal('fitapp', ['TimeSeriesDataType'])

        # Adding unique constraint on 'TimeSeriesDataType', fields ['category', 'resource']
        db.create_unique('fitapp_timeseriesdatatype', ['category', 'resource'])

        # Adding model 'TimeSeriesData'
        db.create_table('fitapp_timeseriesdata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm[user_orm_label])),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['fitapp.TimeSeriesDataType'])),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('value', self.gf('django.db.models.fields.CharField')(default=None, max_length=32, null=True)),
        ))
        db.send_create_signal('fitapp', ['TimeSeriesData'])

        # Adding unique constraint on 'TimeSeriesData', fields ['user', 'resource_type', 'date']
        db.create_unique('fitapp_timeseriesdata', ['user_id', 'resource_type_id', 'date'])


    def backwards(self, orm):
        # Removing unique constraint on 'TimeSeriesData', fields ['user', 'resource_type', 'date']
        db.delete_unique('fitapp_timeseriesdata', ['user_id', 'resource_type_id', 'date'])

        # Removing unique constraint on 'TimeSeriesDataType', fields ['category', 'resource']
        db.delete_unique('fitapp_timeseriesdatatype', ['category', 'resource'])

        # Deleting model 'TimeSeriesDataType'
        db.delete_table('fitapp_timeseriesdatatype')

        # Deleting model 'TimeSeriesData'
        db.delete_table('fitapp_timeseriesdata')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_label: {
            'Meta': {
                'object_name': User.__name__,
                'db_table': "'%s'" % User._meta.db_table
            },
            User._meta.pk.attname: (
                'django.db.models.fields.AutoField', [],
                {'primary_key': 'True',
                'db_column': "'%s'" % User._meta.pk.column}
            ),
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'fitapp.timeseriesdata': {
            'Meta': {'unique_together': "(('user', 'resource_type', 'date'),)", 'object_name': 'TimeSeriesData'},
            'date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['fitapp.TimeSeriesDataType']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['%s']" % user_orm_label}),
            'value': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '32', 'null': 'True'})
        },
        'fitapp.timeseriesdatatype': {
            'Meta': {'unique_together': "(('category', 'resource'),)", 'object_name': 'TimeSeriesDataType'},
            'category': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'fitapp.userfitbit': {
            'Meta': {'object_name': 'UserFitbit'},
            'auth_secret': ('django.db.models.fields.TextField', [], {}),
            'auth_token': ('django.db.models.fields.TextField', [], {}),
            'fitbit_user': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['%s']" % user_orm_label, 'unique': 'True'})
        }
    }

    complete_apps = ['fitapp']
