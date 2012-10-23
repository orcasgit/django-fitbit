# Your Fitbit access credentials, which must be requested from Fitbit.
# You must provide these in your project's settings.
FITAPP_CONSUMER_KEY = None
FITAPP_CONSUMER_SECRET = None

# Where to redirect to after Fitbit authentication is successfully completed.
FITAPP_LOGIN_REDIRECT = '/'

# Where to redirect to after Fitbit authentication credentials have been
# removed.
FITAPP_LOGOUT_REDIRECT = '/'

# The template to use when an unavoidable error occurs during Fitbit
# integration.
FITAPP_ERROR_TEMPLATE = 'fitapp/error.html'
