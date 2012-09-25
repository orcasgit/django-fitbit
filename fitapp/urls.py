from django.conf.urls import patterns, include, url

from fitapp import views


urlpatterns = patterns('',

    # OAuth authentication
    url('^oauth/login/$',
            views.oauth_login, name='oauth-login'),
    url('^oauth/callback/$',
            views.oauth_callback, name='oauth-callback'),

    url('^one/$',
            views.fitbit_data, kwargs={'days': 1}, name='one-day'),
    url('^seven/$',
            views.fitbit_data, kwargs={'days': 7}, name='seven-day'),
    url('^thirty/$',
            views.fitbit_data, kwargs={'days': 30}, name='thirty-day'),

)
