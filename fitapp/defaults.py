# Your Fitbit access credentials, which must be requested from Fitbit.
# You must provide these in your project's settings.
FITAPP_CONSUMER_KEY = None
FITAPP_CONSUMER_SECRET = None

# The verification code for verifying subscriber endpoints
FITAPP_VERIFICATION_CODE = None

# Where to redirect to after Fitbit authentication is successfully completed.
FITAPP_LOGIN_REDIRECT = '/'

# Where to redirect to after Fitbit authentication credentials have been
# removed.
FITAPP_LOGOUT_REDIRECT = '/'

# By default, don't subscribe to user data. Set this to true to subscribe.
FITAPP_SUBSCRIBE = False

# The template to use when an unavoidable error occurs during Fitbit
# integration.
FITAPP_ERROR_TEMPLATE = 'fitapp/error.html'

# The default message used by the fitbit_integration_warning decorator to
# inform the user about Fitbit integration. If a callable is given, it is
# called with the request as the only parameter to get the final value for the
# message.
FITAPP_DECORATOR_MESSAGE = 'This page requires Fitbit integration.'
