from functools import wraps

from django.contrib import messages

from . import utils


DEFAULT_MESSAGE_TEXT = "This page requires Fitbit integration."


def fitbit_required(msg=None):
    """
    Adds a message to inform the user about Fitbit integration if their
    account is not already integrated with Fitbit.

    :param msg: The message text to use if the user is not integrated. If msg
        is a callable, it is called with the request as the only parameter.
        Otherwise, msg is passed in as the message text. Default value: "This
        page requires Fitbit integration."

    Example::

        from django.contrib.auth.decorators import login_required
        from fitapp.decorators import fitbit_required

        @fitbit_required(msg="You should integrate your account with Fitbit!")
        @login_required
        def my_view(request):
            ...

    In this example, the fitbit_required decorator only operates if the user
    is logged in.

    The template(s) for any view with this decorator should display a user's
    messages.
    """
    def inner_decorator(view_func):
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not utils.is_integrated(user):
                text = msg(request) if callable(msg) else msg
                if text is None:
                    text = DEFAULT_MESSAGE_TEXT
                messages.error(request, text)
            return view_func(request, *args, **kwargs)
        return wraps(view_func)(wrapped)
    return inner_decorator
