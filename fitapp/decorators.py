from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import redirect

from . import utils


def fitbit_required(view_func):
    """
    Adds a message to inform the user about Fitbit integration if their
    account is not already integrated with Fitbit.

    The template(s) for any view with this decorator should display a user's
    messages.
    """
    def wrapper(request, *args, **kwargs):
        user = request.user
        if not utils.is_integrated(user):
            url = '{0}?next={1}'.format(reverse('fitbit'), request.path)
            error_msg = 'Oh no! We can\'t display your physical activity ' \
                    'data because your account isn\'t with Fitbit. Please ' \
                    '<a href=\'{0}\'>integrate your account</a> so that we ' \
                    'can track your progress.'.format(url)
            messages.error(request, error_msg)
        return view_func(request, *args, **kwargs)
    return wrapper
