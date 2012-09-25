from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render

from fitapp import utils


@login_required
def oauth_login(request):
    fb = utils.create_fitbit()
    callback_url = request.build_absolute_uri(reverse('oauth-callback'))
    parameters = {'oauth_callback': callback_url}
    token = fb.client.fetch_request_token(parameters)
    token_url = fb.client.authorize_token_url(token)
    request.session['token'] = token
    return redirect(token_url)


@login_required
def oauth_callback(request):
    # store credentials in userfitback model
    return redirect(reverse('one-day'))

def fitbit_data(request, days=1):
    return render(request, 'fitapp/data.html', {})
