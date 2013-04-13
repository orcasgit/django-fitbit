# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'TimeSeriesDataType'
        db.create_table('fitapp_timeseriesdatatype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('category', self.gf('django.db.models.fields.IntegerField')()),
            ('resource', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('unit_type', self.gf('django.db.models.fields.IntegerField')(null=True)),
        ))
        db.send_create_signal('fitapp', ['TimeSeriesDataType'])

        # Adding model 'TimeSeriesData'
        db.create_table('fitapp_timeseriesdata', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'])),
            ('resource_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['fitapp.TimeSeriesDataType'])),
            ('date', self.gf('django.db.models.fields.DateField')()),
            ('value', self.gf('django.db.models.fields.FloatField')(default=None, null=True)),
            ('dirty', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('fitapp', ['TimeSeriesData'])

        # Adding unique constraint on 'TimeSeriesData', fields ['user', 'resource_type', 'date']
        db.create_unique('fitapp_timeseriesdata', ['user_id', 'resource_type_id', 'date'])

        # Adding model 'Unit'
        db.create_table('fitapp_unit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('locale', self.gf('django.db.models.fields.IntegerField')()),
            ('unit_type', self.gf('django.db.models.fields.IntegerField')()),
            ('unit_name', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('fitapp', ['Unit'])

        # Adding unique constraint on 'Unit', fields ['locale', 'unit_type']
        db.create_unique('fitapp_unit', ['locale', 'unit_type'])


    def backwards(self, orm):
        # Removing unique constraint on 'Unit', fields ['locale', 'unit_type']
        db.delete_unique('fitapp_unit', ['locale', 'unit_type'])

        # Removing unique constraint on 'TimeSeriesData', fields ['user', 'resource_type', 'date']
        db.delete_unique('fitapp_timeseriesdata', ['user_id', 'resource_type_id', 'date'])

        # Deleting model 'TimeSeriesDataType'
        db.delete_table('fitapp_timeseriesdatatype')

        # Deleting model 'TimeSeriesData'
        db.delete_table('fitapp_timeseriesdata')

        # Deleting model 'Unit'
        db.delete_table('fitapp_unit')


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
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
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
            'dirty': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['fitapp.TimeSeriesDataType']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'value': ('django.db.models.fields.FloatField', [], {'default': 'None', 'null': 'True'})
        },
        'fitapp.timeseriesdatatype': {
            'Meta': {'object_name': 'TimeSeriesDataType'},
            'category': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'resource': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'unit_type': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        'fitapp.unit': {
            'Meta': {'unique_together': "(('locale', 'unit_type'),)", 'object_name': 'Unit'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locale': ('django.db.models.fields.IntegerField', [], {}),
            'unit_name': ('django.db.models.fields.IntegerField', [], {}),
            'unit_type': ('django.db.models.fields.IntegerField', [], {})
        },
        'fitapp.userfitbit': {
            'Meta': {'object_name': 'UserFitbit'},
            'auth_secret': ('django.db.models.fields.TextField', [], {}),
            'auth_token': ('django.db.models.fields.TextField', [], {}),
            'fitbit_user': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['fitapp']