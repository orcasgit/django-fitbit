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

The URL to which to redirect the user after successful Fitbit integration, if
no 'next' URL is known.

Default:  ``'/'``

.. _FITAPP_LOGOUT_REDIRECT:

FITAPP_LOGOUT_REDIRECT
----------------------

The URL to which to redirect the user after removal of Fitbit account
credentials, if no 'next' URL is known.

Default: ``'/'``

.. _FITAPP_ERROR_TEMPLATE:

FITAPP_ERROR_TEMPLATE
---------------------

The template used to report an error integrating the user's Fitbit.

Default:  ``'fitapp/error.html'``
