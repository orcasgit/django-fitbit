0.2.6 (2016-12-14)
==================

- Add exponential back-off and random jitter to task retries
- Enable some configuration around subscriptions:
  - FITAPP_SUBSCRIPTIONS: List exactly which subscriptions to retrieve and the order to retrieve them in
  - FITAPP_HISTORICAL_INIT_DELAY: The initial delay (in seconds) to wait before retrieving any historic data
  - FITAPP_BETWEEN_DELAY: The delay (in seconds) to wait between retrieving each type of resource

0.2.5 (2016-11-03)
==================

- Add docstrings to all models, help_text to all fields

0.2.4 (2016-05-04)
==================

- More refresh token bugfixes

0.2.2 (2016-03-30)
==================

- Refresh token bugfixes
- Use fitbit==0.2.2

0.2.0 (2016-03-23)
==================

- Integrate with python-fitbit OAuth2 (fitbit==0.2)
- Update documentation to state that `FITAPP_CONSUMER_KEY` should be the OAuth 2.0 client id

0.1.2
=====

- Enable fitbit subscriber verification
- Better error handling in celery tasks

0.1.1
=====

- Fix packaging issue (missing fixture data)

0.1.0
=====

- Support for subscribing to time series data
- Many bug fixes

0.0.1
=====

- Initial release
