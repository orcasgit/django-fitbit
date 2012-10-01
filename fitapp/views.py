from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render

from fitapp.models import UserFitbit
from fitapp import utils
from fitapp.decorators import fitbit_required


@login_required
def fitbit(request):
    """View the status of user's Fitbit Oauth credentials."""
    next_url = request.GET.get('next', None)
    request.session['fitbit_next'] = next_url
    return render(request, 'fitapp/index.html', {
        'active': 'fitbit',
    })


@login_required
def login(request):
    """
    Begin the OAuth authentication process by obtaining a Request Token from
    Fitbit and redirecting the user to the Fitbit site for authorization.
    """
    fb = utils.create_fitbit()
    callback_url = request.build_absolute_uri(reverse('fitbit-complete'))
    parameters = {'oauth_callback': callback_url}
    token = fb.client.fetch_request_token(parameters)
    token_url = fb.client.authorize_token_url(token)
    request.session['token'] = token
    return redirect(token_url)


@login_required
def complete(request):
    """Called back from Fitbit after the user grants us authorization."""
    fb = utils.create_fitbit()
    token = request.session['token']
    verifier = request.GET['oauth_verifier']
    try:
        access_token = fb.client.fetch_access_token(token, verifier)
    except:
        return redirect(reverse('fitbit-error'))
    fbuser, created = UserFitbit.objects.get_or_create(user=request.user,
            auth_token=access_token.key, auth_secret=access_token.secret,
            fitbit_user=fb.client.user_id)
    try:
        next_url = request.session.pop('fitbit_next')
    except KeyError:
        next_url = reverse('fitbit')
    return redirect(next_url)


@login_required
def error(request):
    return render(request, 'fitapp/error.html', {})


@login_required
def logout(request):
    """Remove this user's Fitbit credentials."""
    UserFitbit.objects.filter(user=request.user).delete()
    return redirect(reverse('fitbit'))
