Getting started
===============

.. index::
    single: PyPI

1. Add `django-fitbit` to your Django site's requirements, however you prefer, and install it.  It's
   installable from `PyPI <http://pypi.python.org/pypi/django-fitbit/>`_.

.. index::
    single: INSTALLED_APPS

2. Add `django-fitbit` to your INSTALLED_APPS setting::

    INSTALLED_APPS += ['django-fitbit']

3. Add the `django-fitbit` URLs to your URLconf::

    url(r'^accounts/fitbit/', include('fitapp.urls')),

3. Register your site at the `Fitbit developer site <http://dev.fitbit.com/>`_ to get a key and secret.

4. Add settings for :ref:`FITAPP_CONSUMER_KEY` and :ref:`FITAPP_CONSUMER_SECRET`::

    FITAPP_CONSUMER_KEY = 'abcdefg123456'
    FITAPP_CONSUMER_SECRET = 'abcdefg123456'

5. If you need to change the defaults, add settings for :ref:`FITAPP_INTEGRATION_TEMPLATE` and/or
   :ref:`FITAPP_ERROR_TEMPLATE`.

6. To display whether the user has integrated their Fitbit, or change a template behavior, use the
   :ref:`is_integrated_with_fitbit` template filter. Or in a view, call the :py:func:`fitapp.utils.is_integrated` function.

7. To send the user through authorization at the Fitbit site for your app to access their data, send
   them to the :py:func:`fitapp.views.login` view.
