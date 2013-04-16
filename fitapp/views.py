import json

from datetime import timedelta
from dateutil import parser
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from fitbit.exceptions import (HTTPUnauthorized, HTTPForbidden, HTTPNotFound,
        HTTPConflict, HTTPServerError, HTTPBadRequest)

from . import forms
from . import utils
from .models import UserFitbit, TimeSeriesData, TimeSeriesDataType


@login_required
def login(request):
    """
    Begins the OAuth authentication process by obtaining a Request Token from
    Fitbit and redirecting the user to the Fitbit site for authorization.

    When the user has finished at the Fitbit site, they will be redirected
    to the :py:func:`fitapp.views.complete` view.

    If 'next' is provided in the GET data, it is saved in the session so the
    :py:func:`fitapp.views.complete` view can redirect the user to that URL
    upon successful authentication.

    URL name:
        `fitbit-login`
    """
    next_url = request.GET.get('next', None)
    if next_url:
        request.session['fitbit_next'] = next_url
    else:
        request.session.pop('fitbit_next', None)

    fb = utils.create_fitbit()
    callback_url = request.build_absolute_uri(reverse('fitbit-complete'))
    parameters = {'oauth_callback': callback_url}
    token = fb.client.fetch_request_token(parameters)
    token_url = fb.client.authorize_token_url(token)
    request.session['token'] = token
    return redirect(token_url)


@login_required
def complete(request):
    """
    After the user authorizes us, Fitbit sends a callback to this URL to
    complete authentication.

    If there was an error, the user is redirected again to the `error` view.

    If the authorization was successful, the credentials are stored for us to
    use later, and the user is redirected. If 'next_url' is in the request
    session, the user is redirected to that URL. Otherwise, they are
    redirected to the URL specified by the setting
    :ref:`FITAPP_LOGIN_REDIRECT`.

    If :ref:`FITAPP_SUBSCRIBE` is set to True, add a subscription to user
    data at this time.

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
    # Add the Fitbit user info to the session
    request.session['fitbit_profile'] = fb.user_profile_get()
    if utils.get_setting('FITAPP_SUBSCRIBE'):
        # Create dirty data for all days the user has been in the program,
        # user a bulk create lower query counts. This is only 3 queries
        profile = request.session['fitbit_profile']
        tz = timezone.pytz.timezone(profile['user']['timezone'])
        start = tz.normalize(request.user.date_joined).date()
        now = tz.normalize(timezone.now()).date()
        current = start
        increment = timedelta(days=1)
        existing_data = TimeSeriesData.objects.filter(
            user=request.user).values_list('date', 'resource_type')
        resource_types = list(TimeSeriesDataType.objects.all())
        new_data = []
        while current <= now:
            for resource_type in resource_types:
                kwargs = {'user': request.user, 'date': current,
                          'resource_type': resource_type}
                if not (current, resource_type.pk) in existing_data:
                    new_data.append(TimeSeriesData(dirty=True, **kwargs))
            current = current + increment
        TimeSeriesData.objects.bulk_create(new_data)
        try:
            SUBSCRIBER_ID = utils.get_setting('FITAPP_SUBSCRIBER_ID')
        except ImproperlyConfigured:
            return redirect(reverse('fitbit-error'))
        fb.subscription(request.user.id, SUBSCRIBER_ID)

    next_url = request.session.pop('fitbit_next', None) or utils.get_setting(
            'FITAPP_LOGIN_REDIRECT')
    return redirect(next_url)


@receiver(user_logged_in)
def create_fitbit_session(sender, request, user, **kwargs):
    """ If the user is a fitbit user, update the profile in the session. """

    if user.is_authenticated() and utils.is_integrated(user) and \
            user.is_active:
        fbuser = UserFitbit.objects.filter(user=user)
        if fbuser.exists():
            fb = utils.create_fitbit(**fbuser[0].get_user_data())
            try:
                request.session['fitbit_profile'] = fb.user_profile_get()
            except:
                pass


@login_required
def error(request):
    """
    The user is redirected to this view if we encounter an error acquiring
    their Fitbit credentials. It renders the template defined in the setting
    :ref:`FITAPP_ERROR_TEMPLATE`. The default template, located at
    *fitapp/error.html*, simply informs the user of the error::

        <html>
            <head>
                <title>Fitbit Authentication Error</title>
            </head>
            <body>
                <h1>Fitbit Authentication Error</h1>

                <p>We encontered an error while attempting to authenticate you
                through Fitbit.</p>
            </body>
        </html>

    URL name:
        `fitbit-error`
    """
    return render(request, utils.get_setting('FITAPP_ERROR_TEMPLATE'), {})


@login_required
def logout(request):
    """Forget this user's Fitbit credentials.

    If the request has a `next` parameter, the user is redirected to that URL.
    Otherwise, they're redirected to the URL defined in the setting
    :ref:`FITAPP_LOGOUT_REDIRECT`.

    URL name:
        `fitbit-logout`
    """
    user = request.user
    fbuser = UserFitbit.objects.filter(user=user)
    if utils.get_setting('FITAPP_SUBSCRIBE'):
        try:
            fb = utils.create_fitbit(**fbuser[0].get_user_data())
            subs = fb.list_subscriptions()['apiSubscriptions']
            if '%s' % user.id in [s['subscriptionId'] for s in subs]:
                SUBSCRIBER_ID = utils.get_setting('FITAPP_SUBSCRIBER_ID')
                fb.subscription(user.id, SUBSCRIBER_ID, method="DELETE")
        except:
            return redirect(reverse('fitbit-error'))
    fbuser.delete()
    next_url = request.GET.get('next', None) or utils.get_setting(
            'FITAPP_LOGOUT_REDIRECT')
    return redirect(next_url)


@csrf_exempt
@require_POST
def update(request):
    """Receive notification from Fitbit.

    Loop through the updates and mark the respective data as dirty.

    URL name:
        `fitbit-update`
    """

    # The updates come in as a json file in a form POST
    if request.FILES:
        try:
            updates = json.loads(request.FILES['updates'].read())
            all_types = TimeSeriesDataType.objects.all()
            # Use bulk updates and inserts to reduce queries.
            for update in updates:
                user_fitbit = UserFitbit.objects.get(
                    user_id=update['subscriptionId'],
                    fitbit_user=update['ownerId'])
                cat = getattr(TimeSeriesDataType, update['collectionType'])
                cat_types = all_types.filter(category=cat)
                kwargs = {'user': user_fitbit.user, 'date': update['date']}
                # Update existing data
                existing_data = TimeSeriesData.objects.filter(
                    resource_type__in=cat_types, **kwargs)
                existing_data.update(dirty=True)
                # Create dirty records for non-existent data
                existing_types = [ed.resource_type.pk for ed in existing_data]
                new_res = cat_types.exclude(pk__in=existing_types)
                TimeSeriesData.objects.bulk_create([
                    TimeSeriesData(resource_type=res, dirty=True, **kwargs)
                    for res in new_res
                ])

        except:
            return redirect(reverse('fitbit-error'))

        return HttpResponse(status=204)

    # if someone enters the url into the browser, raise a 404
    raise Http404


def make_response(code=None, objects=[]):
    """AJAX helper method to generate a response"""

    data = {
        'meta': {'total_count': len(objects), 'status_code': code},
        'objects': objects,
    }
    return HttpResponse(json.dumps(data))


def normalize_date_range(fitbit_data):
    """Prepare a fitbit date range for django database access. """

    result = {}
    base_date = fitbit_data['base_date']
    if base_date == 'today':
        now = timezone.now()
        if 'fitbit_profile' in request.session.keys():
            tz = request.session['fitbit_profile']['user']['timezone']
            now = timezone.pytz.timezone(tz).normalize(timezone.now())
        base_date = now.date().strftime('%Y-%m-%d')
    result['date__gte'] = base_date

    if 'end_date' in fitbit_data.keys():
        result['date__lte'] = fitbit_data['end_date']
    else:
        period = fitbit_data['period']
        if period != 'max':
            start = parser.parse(base_date)
            if 'y' in period:
                kwargs = {'years': int(period.replace('y', ''))}
            elif 'm' in period:
                kwargs = {'months': int(period.replace('m', ''))}
            elif 'w' in period:
                kwargs = {'weeks': int(period.replace('w', ''))}
            elif 'd' in period:
                kwargs = {'days': int(period.replace('d', ''))}
            end_date = start + relativedelta(**kwargs)
            result['date__lte'] = end_date.strftime('%Y-%m-%d')

    return result


@require_GET
def get_steps(request):
    """An AJAX view that retrieves this user's steps data from Fitbit.

    This view may only be retrieved through a GET request. The view can
    retrieve data from either a range of dates, with specific start and end
    days, or from a time period ending on a specific date.

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

    # Manually check that user is logged in and integrated with Fitbit.
    user = request.user
    fitapp_subscribe = utils.get_setting('FITAPP_SUBSCRIBE')
    if not user.is_authenticated() or not user.is_active:
        return make_response(101)
    if not utils.is_integrated(user) and not fitapp_subscribe:
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

    if fitapp_subscribe:
        # Get the data from the database first.
        date_range = normalize_date_range(fitbit_data)
        resource_type = TimeSeriesDataType.objects.get(
            category=TimeSeriesDataType.activities, resource='steps')
        existing_data = TimeSeriesData.objects.filter(
            user=user, resource_type=resource_type, **date_range)
        if not existing_data.filter(dirty=True).exists()\
                or not utils.is_integrated(user):
            # No dirty data, just return what we have
            clean_data = [{'value': d.value, 'dateTime': d.string_date()}
                          for d in existing_data]
            return make_response(100, clean_data)

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

    if fitapp_subscribe:
        # If we are here then that means there was dirty data that needs to
        # be updated.
        kwargs = {'user': user, 'resource_type': resource_type}
        kwargs.update(date_range)
        existing_data = TimeSeriesData.objects.filter(**kwargs).values_list(
            'date', 'resource_type', 'dirty')
        new_data = []
        for step in steps:
            # Update existing dirty data or create new record
            date = parser.parse(step['dateTime']).date()
            if (date, resource_type.pk, True) in existing_data:
                TimeSeriesData.objects.filter(date=date, **kwargs).update(
                    value=step['value'], dirty=False)
            elif (date, resource_type.pk, False) not in existing_data:
                new_data.append(TimeSeriesData(
                    user=user, date=date, value=step['value'],
                    dirty=False, resource_type=resource_type))
        TimeSeriesData.objects.bulk_create(new_data)
        # Delete any local dirty data, that doesn't have corresponding data
        # from Fitbit
        TimeSeriesData.objects.filter(dirty=True, **kwargs).delete()

    return make_response(100, steps)
