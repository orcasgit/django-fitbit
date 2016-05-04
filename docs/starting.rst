Getting started
===============

.. index::
    single: PyPI

1. Add `django-fitbit` to your Django site's requirements, however you prefer,
   and install it.  It's installable from `PyPI
   <http://pypi.python.org/pypi/django-fitbit/>`_.

.. index::
    single: INSTALLED_APPS

2. Add `fitapp` to your INSTALLED_APPS setting::

    INSTALLED_APPS += ['fitapp']

3. Add the `django-fitbit` URLs to your URLconf::

    url(r'^fitbit/', include('fitapp.urls')),

3. Register your site at the `Fitbit developer site <http://dev.fitbit.com/>`_
   to get a key and secret.

4. Add settings for :ref:`FITAPP_CONSUMER_KEY` and
   :ref:`FITAPP_CONSUMER_SECRET`::

    FITAPP_CONSUMER_KEY = '9898XH'
    FITAPP_CONSUMER_SECRET = 'abcdefg123456'

5. If you need to change the defaults, add settings for
   :ref:`FITAPP_LOGIN_REDIRECT`, :ref:`FITAPP_LOGOUT_REDIRECT`, and/or
   :ref:`FITAPP_ERROR_TEMPLATE`.

6. To display whether the user has integrated their Fitbit, or change a
   template behavior, use the :ref:`is_integrated_with_fitbit` template
   filter. Or in a view, call the :py:func:`fitapp.utils.is_integrated`
   function. You can also use the decorator
   :py:func:`fitapp.decorators.fitbit_integration_warning` to display a message to the
   user when they are not integrated with Fitbit.

7. To send the user through authorization at the Fitbit site for your app to
   access their data, send them to the :py:func:`fitapp.views.login` view.

8. To get step data for a user from a web page, use the AJAX
   :py:func:`fitapp.views.get_steps` view.

9. If you are using sqlite, you will want to create a celery configuration that
   prevents the fitapp celery tasks from being executed concurrently. If you
   are using any other database type, you can skip this step.
