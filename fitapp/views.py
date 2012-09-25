from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render

from fitapp import models as fitapp
from fitapp import utils


@login_required
def oauth(request):
    return render(request, 'fitapp/oauth/index.html', {})


@login_required
def oauth_login(request):
    fb = utils.create_fitbit()
    callback_url = request.build_absolute_uri(reverse('oauth-complete'))
    parameters = {'oauth_callback': callback_url}
    token = fb.client.fetch_request_token(parameters)
    token_url = fb.client.authorize_token_url(token)
    request.session['token'] = token
    return redirect(token_url)


@login_required
def oauth_complete(request):
    fb = utils.create_fitbit()
    token = request.session['token']
    verifier = request.GET['oauth_verifier']
    try:
        access_token = fb.client.fetch_access_token(token, verifier)
    except:
        return redirect(reverse('oauth-error'))
    fbuser, created = fitapp.UserFitbit.objects.get_or_create(user=request.user,
            auth_token=access_token.key, auth_secret=access_token.secret,
            fitbit_user=fb.client.user_id)
    return redirect(reverse('one-day'))


def oauth_error(request):
    return render(request, 'fitapp/oauth/error.html')


def fitbit_data(request, days=1):
    return render(request, 'fitapp/data.html', {})
