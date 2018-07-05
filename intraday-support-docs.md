How to get intraday support to work

- There must be a FITAPP_GET_INTRADAY boolean setting somewhere in the Django project's settings files.
If True, django-fitbit will retrieve and create records for intraday data for any TimeSeriesDataType marked
as intraday-compatible.
- When TimeSeriesDataTypes are created, they must be given

What was changed
- Add FITAPP_GET_INTRADAY setting to:
    - fitapp/defaults.py - False
    - test_settings.py - True