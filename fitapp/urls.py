from django.urls import re_path

from . import views


urlpatterns = [
    # OAuth authentication
    re_path(r'^login/$', views.login, name='fitbit-login'),
    re_path(r'^complete/$', views.complete, name='fitbit-complete'),
    re_path(r'^error/$', views.error, name='fitbit-error'),
    re_path(r'^logout/$', views.logout, name='fitbit-logout'),

    # Subscriber callback for near realtime updates
    re_path(r'^update/$', views.update, name='fitbit-update'),

    # Fitbit data retrieval
    re_path(r'^get_data/(?P<category>[\w]+)/(?P<resource>[/\w]+)/$',
        views.get_data, name='fitbit-data'),
    re_path(r'^get_steps/$', views.get_steps, name='fitbit-steps')
]
