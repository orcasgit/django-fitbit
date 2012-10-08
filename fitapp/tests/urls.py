
from django.conf.urls import patterns, include, url


def test(request):
    return HttpResponse('')


urlpatterns = patterns('',

    url(r'', include('fitapp.urls')),

    url(r'^test/$', test, name='test'),  # A sample URL to redirect to
)
