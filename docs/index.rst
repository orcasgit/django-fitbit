.. django-fitbit documentation master file, created by
   sphinx-quickstart on Tue Oct  9 08:03:08 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to django-fitbit's documentation!
=========================================

Contents:

.. toctree::
   :maxdepth: 2

   starting
   settings
   views
   templatetags
   utils
   links
   releases

Django-fitbit is a Django app for integrating a user's Fitbit data into your
site.

It handles the details of getting your app authorized to access your user's
Fitbit data via the Fitbit web API.

Testing
=======

Please add tests for any changes you submit.

To install all the requirements for running the tests::

    pip install -r requirements/dev.txt

To run the tests for specific python version (ie. py27-1.8.X)::

    tox -e py27-1.8.X

If you would like to run specific test you can bypass tox altogether and run::

    python -m run_tests fitapp.tests.test_integration.TestLoginView.test_unauthenticated

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

