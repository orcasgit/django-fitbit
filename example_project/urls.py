from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth import views as auth_views


admin.autodiscover()

urlpatterns = patterns('',

    # Django account authentication
    url('^accounts/login/$',
            auth_views.login, name='account_login'),
    url('^accounts/logout/$',
            auth_views.logout_then_login, name='account_logout'),

    # Fitapp URLs
    url(r'', include('fitapp.urls')),

)
