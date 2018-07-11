How to get intraday support to work

- There must be a FITAPP_GET_INTRADAY boolean setting somewhere in the Django project's settings files.
If True, django-fitbit will retrieve and create records for intraday data for any TimeSeriesDataType marked
as intraday-compatible.
- When TimeSeriesDataTypes are created, they must be given intraday_support = True
    - VERY IMPORTANT: There are not currently checks to see if the given Fitbit app has authorization for
    a certain category of intraday data. Be sure your app has authorization before attempting to retrieve it.

- Intraday TimeSeriesData instances will be marked with intraday = True.


What was changed
- Add FITAPP_GET_INTRADAY setting to:
    - fitapp/defaults.py - False
    - test_settings.py - True

- Changes to fitapp/models.py
    - Add intraday_support field to TimeSeriesDataType, defaults to False.
    - Add intraday field to TimeSeriesData, defaults to False.
    - Change date field for TimeSeriesData from DateField to DateTimeField, change help text to reflect this.
        - NOTE: I would like to change the name of this field to date_time.
    - Change unique_together values for TimeSeriesData by adding 'intraday' as a requirement.

Changes to fitapp/migrations
    - Move addition of TimeSeriesDataType.intraday_support to 0001_initial.py to resolve errors.
    - Add intraday_support field to every TimeSeriesDataType in fitapp/fixtures/initial_data.json to resolve errors.

- Changes to fitapp/views.py
    - Change

- Changes to fitapp/tasks.py
    - Add currently empty get_intraday_data task.


Planned changes
Have fitbit listener view call a different task depending on if data is intraday or not.
Probably need to add fitapp subscriptions value for test settings?