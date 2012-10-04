from django.conf.urls import patterns, include, url

from . import views


urlpatterns = patterns('',

    # OAuth authentication
    url('^$',
            views.fitbit, name='fitbit'),
    url('^login/$',
            views.login, name='fitbit-login'),
    url('^complete/$',
            views.complete, name='fitbit-complete'),
    url('^error/$',
            views.error, name='fitbit-error'),
    url('^logout/$',
            views.logout, name='fitbit-logout'),
)
