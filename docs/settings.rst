Settings
========

.. index::
    single: FITAPP_CONSUMER_KEY

.. _FITAPP_CONSUMER_KEY:

FITAPP_CONSUMER_KEY
-------------------

The key assigned to your app by Fitbit when you register your app at
`the Fitbit developer site <http://dev.fitbit.com/>`_. You must specify a
non-null value for this setting.

.. index::
    single: FITAPP_CONSUMER_SECRET

.. _FITAPP_CONSUMER_SECRET:

FITAPP_CONSUMER_SECRET
----------------------

The secret that goes with the FITAPP_CONSUMER_KEY. You must specify a non-null
value for this setting.

.. _FITAPP_LOGIN_REDIRECT:

FITAPP_LOGIN_REDIRECT
---------------------

:Default:  ``'/'``

The URL which to redirect the user to after successful Fitbit integration, if
no forwarding URL is given in the 'fitapp_next' session variable.

.. _FITAPP_LOGOUT_REDIRECT:

FITAPP_LOGOUT_REDIRECT
----------------------

:Default: ``'/'``

The URL which to redirect the user to after removal of Fitbit account
credentials, if no forwarding URL is given in the 'next' GET parameter.

.. _FITAPP_SUBSCRIBE:

FITAPP_SUBSCRIBE
----------------

:Default: ``False``

When this setting is True, we will subscribe to user data. Fitbit will
send notifications when the data changes and we will queue tasks to get
the updated data. When requests for fitbit data are made to fitapp, we
will always pull the latest data from our own database instead of getting
it directly from Fitbit. To use this feature, you will need to setup a
celery worker to handle the tasks.

Example celery configuration with rabbitmq as a backend:

FITAPP_QUEUE = "fitapp_get_data"
CELERY_ROUTES = {'fitapp.tasks.update_fitbit_data_task':
                 {'queue': FITAPP_QUEUE}}
BROKER_URL = "amqp://user:password@your_host:5672/your_vhost"
import djcelery
djcelery.setup_loader()


.. _FITAPP_SUBSCRIBER_ID:

FITAPP_SUBSCRIBER_ID
--------------------

This setting is only applicable if :ref:`FITAPP_SUBSCRIBE` is True. This is
the unique ID of the subscriber endpoint that was set up for your Fitbit
app on their developer site.

.. _FITAPP_ERROR_TEMPLATE:

FITAPP_ERROR_TEMPLATE
---------------------

:Default:  ``'fitapp/error.html'``

The template used to report an error integrating the user's Fitbit.

.. _FITAPP_DECORATOR_MESSAGE:

FITAPP_DECORATOR_MESSAGE
------------------------

:Default: ``'This page requires Fitbit integration.'``

The default message used by the
:py:func:`fitapp.decorators.fitbit_integration_warning` decorator to inform
the user about Fitbit integration. If a callable is provided, it is called
with the request as the only parameter to get the final value for the message.
