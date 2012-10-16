import json

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

from fitbit.exceptions import (HTTPUnauthorized, HTTPForbidden, HTTPNotFound,
        HTTPConflict, HTTPServerError, HTTPBadRequest)

from . import forms
from . import utils
from .models import UserFitbit


@login_required
def fitbit(request):
    """View the status of user's Fitbit Oauth credentials.

    Uses the template from the setting :ref:`FITAPP_INTEGRATION_TEMPLATE`

    URL name:
        `fitbit`

    Simple example::

        {% load url from future %}
        {% load fitbit %}

        <html>
            <head>
                <title>Fitbit Integration</title>
            </head>
            <body>
                {% if request.user|is_integrated_with_fitbit %}
                    <p><a href="{% url 'fitbit-logout' %}">Remove Fitbit integration from this account</a></p>
                {% else %}
                    <p><a href="{% url 'fitbit-login' %}">Integrate your account with Fitbit</a></p>
                {% endif %}
            </body>
        </html>

    """
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

    When the user has finished at the Fitbit site, they'll be redirected
    to the :py:func:`fitapp.views.complete` view.

    URL name:
        `fitbit-login`
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
    """The user is redirected here by Fitbit after the user grants us authorization.

    If there was an error, the user is redirected again to the `error` view.

    If the authorization was successful, the credentials are stored for us to use
    later, and the user is redirected.  If the user came here via the link displayed
    by the :py:func:`fitapp.decorators.fitbit_required` decorator, then the user is redirected
    to the view they were originally trying to get to.  Otherwise, they're redirected to the
    :py:func:`fitapp.views.fitbit` view.

    URL name:
        `fitbit-complete`

    """
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
    """The user is redirected to this view if there's an error acquiring their Fitbit credentials.

    URL name:
        `fitbit-error`

    Uses the template from the setting :ref:`FITAPP_ERROR_TEMPLATE`.

    The default template just tells them there was an error and offers a link to try again::

        {% load url from future %}

        <html>
            <head>
                <title>Fitbit Authentication Error</title>
            </head>
            <body>
                <h1>Fitbit Authentication Error</h1>

                <p>We encountered an error while attempting to authenticate you through Fitbit.</p>

                <p><a href="{% url 'fitbit' %}">Retry Fitbit Authentication</a></p>
            </body>
        </html>

    """
    return render(request, utils.get_setting('FITAPP_ERROR_TEMPLATE'), {})


@login_required
def logout(request):
    """Forget this user's Fitbit credentials.

    If the request has a `next` parameter, the user is redirected to that URL.
    Otherwise, they're redirected to the :py:func:`fitapp.views.fitbit` view.

    URL name:
        `fitbit-logout`
    """
    UserFitbit.objects.filter(user=request.user).delete()
    next_url = request.GET.get('next', None) or reverse('fitbit')
    return redirect(next_url)


@require_GET
def get_steps(request):
    """An AJAX view that retrieves this user's steps data from Fitbit.

    :param request: The HTTPRequest object. This view may only be retrieved
        through a GET request.

    The view can retrieve data from either a range of dates, with specific
    start and end days, or from a time period ending on a specific date.

    To retrieve a specific time period, two GET parameters are used:

        :period: A string describing the time period, ending on *base_date*,
            for which to retrieve data - one of '1d', '7d', '30d', '1w', '1m',
            '3m', '6m', '1y', or 'max.
        :base_date: The last date (in the format 'yyyy-mm-dd') of the
            requested period. If not provided, then *base_date* is
            assumed to be today.

    To retrieve a range of dates, two GET parameters are used:

        :base_date: The first day of the range, in the format 'yyyy-mm-dd'.
        :end_date: The final day of the range, in the format 'yyyy-mm-dd'.

    The response body contains a JSON-encoded map with two items:

        :objects: an ordered list (from oldest to newest) of daily steps data
            for the requested period. Each day is of the format::

               {'dateTime': 'yyyy-mm-dd', 'value': 123}

           where the user took *value* steps on *dateTime*.
        :meta: a map containing two things: the *total_count* of objects, and
            the *status_code* of the response.

    When everything goes well, the *status_code* is 100 and the requested data
    is included. However, there are a number of things that can 'go wrong'
    with this call. For each type of error, we return an empty data list with
    a *status_code* to describe what went wrong on our end:

        :100: OK - Response contains JSON steps data.
        :101: User is not logged in.
        :102: User is not integrated with Fitbit.
        :103: Fitbit authentication credentials are invalid and have been
            removed.
        :104: Invalid input parameters. Either *period* or *end_date*, but not
            both, must be supplied. *period* should be one of [1d, 7d, 30d,
            1w, 1m, 3m, 6m, 1y, max], and dates should be of the format
            'yyyy-mm-dd'.
        :105: User exceeded the Fitbit limit of 150 calls/hour.
        :106: Fitbit error - please try again soon.

    See also the `Fitbit API doc for Get Time Series
    <https://wiki.fitbit.com/display/API/API-Get-Time-Series>`_.

    URL name:
        `fitbit-steps`
    """
    def make_response(code=None, steps=None):
        steps = steps or []
        data = {
            'meta': {'total_count': len(steps), 'status_code': code},
            'objects': steps,
        }
        return HttpResponse(json.dumps(data))

    # Manually check that user is logged in and integrated with Fitbit.
    user = request.user
    if not user.is_authenticated() or not user.is_active:
        return make_response(101)
    if not utils.is_integrated(user):
        return make_response(102)

    base_date = request.GET.get('base_date', None)
    period = request.GET.get('period', None)
    end_date = request.GET.get('end_date', None)
    if period and not end_date:
        form = forms.PeriodForm({'base_date': base_date, 'period': period})
    elif end_date and not period:
        form = forms.RangeForm({'base_date': base_date, 'end_date': end_date})
    else:
        # Either end_date or period, but not both, must be specified.
        return make_response(104)

    fitbit_data = form.get_fitbit_data()
    if not fitbit_data:
        return make_response(104)

    # Request steps data through the API and handle related errors.
    fbuser = UserFitbit.objects.get(user=user)
    try:
        steps = utils.get_fitbit_steps(fbuser, **fitbit_data)
    except (HTTPUnauthorized, HTTPForbidden):
        # Delete invalid credentials.
        fbuser.delete()
        return make_response(103)
    except HTTPConflict:
        return make_response(105)
    except HTTPServerError:
        return make_response(106)
    except:
        # Other documented exceptions include TypeError, ValueError,
        # HTTPNotFound, and HTTPBadRequest. But they shouldn't occur, so we'll
        # send a 500 and check it out.
        raise

    return make_response(100, steps)
