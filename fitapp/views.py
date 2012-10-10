import json

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render

from fitbit.exceptions import (HTTPUnauthorized, HTTPForbidden, HTTPNotFound,
        HTTPConflict, HTTPServerError, HTTPBadRequest)

from . import utils
from .models import UserFitbit


@login_required
def fitbit(request):
    """View the status of user's Fitbit Oauth credentials."""
    next_url = request.GET.get('next', None)
    if next_url:
        request.session['fitbit_next'] = next_url
    return render(request, utils.get_setting('FITAPP_INTEGRATION_TEMPLATE'),
            {})


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
    try:
        token = request.session.pop('token')
        verifier = request.GET.get('oauth_verifier')
    except KeyError:
        return redirect(reverse('fitbit-error'))
    try:
        access_token = fb.client.fetch_access_token(token, verifier)
    except:
        return redirect(reverse('fitbit-error'))
    fbuser, _ = UserFitbit.objects.get_or_create(user=request.user)
    fbuser.auth_token = access_token.key
    fbuser.auth_secret = access_token.secret
    fbuser.fitbit_user = fb.client.user_id
    fbuser.save()
    next_url = request.session.pop('fitbit_next', None) or reverse('fitbit')
    return redirect(next_url)


@login_required
def error(request):
    return render(request, utils.get_setting('FITAPP_ERROR_TEMPLATE'), {})


@login_required
def logout(request):
    """Remove this user's Fitbit credentials."""
    UserFitbit.objects.filter(user=request.user).delete()
    next_url = request.GET.get('next', None) or reverse('fitbit')
    return redirect(next_url)


def get_steps(request, period):
    """Retrieves this user's steps data from Fitbit for the requested period.

    The response body contains a JSON-encoded map with two things:
        'objects': an ordered list (from oldest to newest) of daily steps data
                   for the requested period. Each day is of the format:
                        {'dateTime': 'yyyy-mm-dd', 'value': 123}
                   where the user took 'value' steps on 'dateTime'.
           'meta': a map containing two things: the 'total_count' of objects,
                   and the 'status_code' of the response.

    When everything goes well, the status_code is 100 and the requested data
    is included. However, there are a number of things that can 'go wrong'
    with this call. For each exception, we return no data with a status_code
    to describe what went wrong on our end:

    100 OK              no message -- Response contains JSON steps data.
    101 Not Logged In   User is not logged in.
    102 Not Integrated  User is not integrated with Fitbit.
    103 Bad Credentials Fitbit authentication credentials are invalid and have
                        been removed.
    104 Bad Request     Requested period should be one of [1d, 7d, 30d, 1w,
                        1m, 3m, 6m, 1y, max].
    105 Rate Limited    User exceeded the Fitbit limit of 150 calls/hour.
    106 Fitbit Error    Please try again soon.
    """
    def make_response(code=None, steps=None):
        steps = steps or []
        data = {
            'meta': {'total_count': len(steps), 'status_code': code},
            'objects': steps,
        }
        return HttpResponse(json.dumps(data))

    # Check that user is logged in and integrated with Fitbit.
    user = request.user
    if not user.is_authenticated() or not user.is_active:
        return make_response(101)
    if not utils.is_integrated(user):
        return make_response(102)

    # Check that request is for the correct time periods.
    if not period in utils.get_valid_periods():
        return make_response(104)

    # Request steps data through the API and handle related errors.
    fbuser = UserFitbit.objects.get(user=user)
    try:
        steps = utils.get_fitbit_steps(fbuser, period)
    except (HTTPUnauthorized, HTTPForbidden):
        # Delete invalid credentials.
        fbuser.delete()
        return make_response(103)
    except HTTPConflict:
        return make_response(105)
    except HTTPServerError:
        return make_response(106)
    except:
        # Other documented exceptions are ValueError, HTTPNotFound, and
        # HTTPBadRequest. But they shouldn't occur, so we'll send a 500 and
        # check it out.
        raise

    return make_response(100, steps)
