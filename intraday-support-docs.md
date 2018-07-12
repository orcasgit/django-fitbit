Summary for 7/12/18

I'm still trying to get a handle on what changed between the original django-fitbit and our fork.
Particularly the FITAPP_SUBSCRIPTIONS setting in the original django-fitbit - there are no usages of this in the
old MapTrek, and it defaults to None, which would seem to make some of the code not work, but it does.
The old MapTrek uses a setting called FITAPP_SUBSCRIPTION_COLLECTION to enumerate what categories of data
to subscribe to, and this is used when subscriptions are created but i can't exactly figure out
what its role is in actually getting data.

Investigating further I found that FITAPP_SUBSCRIPTIONS is not set in the old Maptrek. (set to None)


When we get a subscription notification, it looks like this:
{
        "collectionType": "activities",
        "date": "2010-03-01",
        "ownerId": "184X36",
        "ownerType": "user",
        "subscriptionId": "2345"
    }
Note that it doesn't specify what kind of activity data is available. Since we only care about steps,
we may get activity notifications that end up being useless because they're not for step data. I'm not sure
but this may be a reason behind the dropped data issue.


How to get intraday support to work

- There must be a FITAPP_GET_INTRADAY boolean setting somewhere in the Django project's settings files.
If True, django-fitbit will retrieve and create records for intraday data for any TimeSeriesDataType marked
as intraday-compatible.
- FITAPP_GET_INTRADAY defaults to False.
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
    - Change the task scheduling portion of the update view to schedule the get_intraday_data task
    when the data needed is intraday enabled, instead of calling get_time_series_data.

- Changes to fitapp/tasks.py
    - Add currently empty get_intraday_data task.


Planned changes

- Add last_intraday_data_from_when or similar field to UserFitbit
- Rewrite get_intraday_data to use appropriate python-fitbit function and to update/maintain last_intraday_data field.
        - Also to ask for a time range instead of a full day of data. 

Have fitbit listener view call a different task depending on if data is intraday or not.
Probably need to add fitapp subscriptions value for test settings?




Unknown number of new settings introduced in fork of django-fitbit
I have yet to figure out how FITAPP_SUBSCRIPTIONS is set in Maptrek.
Fork introduces FITAPP_SUBSCRIPTION_COLLECTION
