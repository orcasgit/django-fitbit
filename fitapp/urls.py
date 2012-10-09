from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns('',

    # OAuth authentication
    url(r'^$',
            views.fitbit, name='fitbit'),
    url(r'^login/$',
            views.login, name='fitbit-login'),
    url(r'^complete/$',
            views.complete, name='fitbit-complete'),
    url(r'^error/$',
            views.error, name='fitbit-error'),
    url(r'^logout/$',
            views.logout, name='fitbit-logout'),


    # Fitbit data retrieval
    url(r'^get_steps/(?P<period>\w+)/',
            views.get_steps, name='fitbit-steps'),
)
