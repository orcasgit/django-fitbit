from django.core.urlresolvers import reverse
from django.shortcuts import redirect, render

from fitapp import utils


def fitbit_required(view_func):
    """
    Redirects the user to the Fitbit integration page if their account is not
    integrated with Fitbit.
    """
    def wrapper(*args, **kwargs):
        request = args[0]
        user = request.user
        if not utils.is_integrated(user):
            url = '{0}?next={1}'.format(reverse('fitbit'), request.path)
            return redirect(url)
        return view_func(*args, **kwargs)
    return wrapper
