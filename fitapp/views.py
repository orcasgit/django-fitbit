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
    request.session['fitbit_next'] = next_url
    return render(request, utils.get_integration_template(), {
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
    try:
        token = request.session.pop('token')
        verifier = request.GET.get('oauth_verifier')
    except KeyError:
        return redirect(reverse('fitbit-error'))
    try:
        access_token = fb.client.fetch_access_token(token, verifier)
    except:
        return redirect(reverse('fitbit-error'))
    fbuser, _ = UserFitbit.objects.get_or_create(user=request.user,
            auth_token=access_token.key, auth_secret=access_token.secret,
            fitbit_user=fb.client.user_id)
    next_url = request.session.pop('fitbit_next', None) or reverse('fitbit')
    return redirect(next_url)


@login_required
def error(request):
    return render(request, utils.get_error_template(), {})


@login_required
def logout(request):
    """Remove this user's Fitbit credentials."""
    UserFitbit.objects.filter(user=request.user).delete()
    next_url = request.GET.get('next', None) or reverse('fitbit')
    return redirect(next_url)


def get_steps(request, period):
    """
    Retrieves this user's steps data from Fitbit for the requested period.

    The data is a JSON-encoded, ordered list (from oldest to newest) of daily
    steps data for the requested period. Each day is of the format:
            {"dateTime": "yyyy-mm-dd", "value": 123}
    where "value" is the number of steps that the user took on "dateTime".

    When everything goes well, we return a 200 response with the requested
    data. However, there are a number of things that can 'go wrong' with this
    call. For each exception, we return a different response code with a
    short descriptive error message.

    200 OK              no message -- Response contains JSON steps data.
    400 Bad Request     Requested period should be one of [1d, 7d, 30d, 1w,
                        1m, 3m, 6m, 1y, max].
    401 Unauthorized    User is not integrated with Fitbit.
    403 Forbidden       Fitbit authentication credentials are invalid.
    404 Not Found       User is not logged in.
    409 Rate Limited    User exceeded the Fitbit limit of 150 calls/hour.
    500 Internal Error  no message -- Error has been logged.
    502 Fitbit Error    Please try again soon.
    """
    # Check that user is logged in and integrated with Fitbit.
    user = request.user
    if not user.is_authenticated() or not user.is_active:
        msg = 'Unauthorized - User is not logged in.'
        return HttpResponse(msg, status=404)
    if not utils.is_integrated(user):
        msg = 'Forbidden - User is not integrated with Fitbit.'
        return HttpResponse(msg, status=401)

    # Check that request is for the correct time periods.
    if not period in ['1d', '7d', '30d', '1w', '1m', '3m', '6m', '1y', 'max']:
        msg = 'Bad Request - Requested period should be one of [1d, 7d, ' \
                '30d, 1w, 1m, 3m, 6m, 1y, max].'
        return HttpResponse(msg, status=400)

    # Request steps data through the API and handle related errors.
    fbuser = UserFitbit.objects.get(user=user)
    try:
        steps = utils.get_fitbit_steps(fbuser, period)
    except (HTTPUnauthorized, HTTPForbidden):
        msg = 'Forbidden - Fitbit authentication credentials are invalid.'
        return HttpResponse(msg, status=403)
    except HTTPConflict:
        msg = 'Rate Limited - User has exceeded Fitbit limit of 150 calls/hour'
        return HttpResponse(msg, status=409)
    except HTTPServerError:
        msg = 'Fitbit Error - Please try again soon.'
        return HttpResponse(msg, status=502)
    except:
        # Other documented exceptions are ValueError, HTTPNotFound, and
        # HTTPBadRequest. But they shouldn't occur, so we'll send a 500 and
        # check it out.
        raise

    data = json.dumps(steps)
    return HttpResponse(data)
