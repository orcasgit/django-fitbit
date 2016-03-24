from django.conf.urls import url

from . import views


urlpatterns = [
    # OAuth authentication
    url(r'^login/$', views.login, name='fitbit-login'),
    url(r'^complete/$', views.complete, name='fitbit-complete'),
    url(r'^error/$', views.error, name='fitbit-error'),
    url(r'^logout/$', views.logout, name='fitbit-logout'),

    # Subscriber callback for near realtime updates
    url(r'^update/$', views.update, name='fitbit-update'),

    # Fitbit data retrieval
    url(r'^get_data/(?P<category>[\w]+)/(?P<resource>[/\w]+)/$',
        views.get_data, name='fitbit-data'),
    url(r'^get_steps/$', views.get_steps, name='fitbit-steps')
]
