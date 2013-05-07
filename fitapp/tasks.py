import logging

from celery import task
from dateutil import parser

from . import utils
from .models import UserFitbit, TimeSeriesData, TimeSeriesDataType


logger = logging.getLogger(__name__)


@task
def update_fitbit_data_task(fitbit_user, category, date):
    logger.debug("FITAPP DATA TASK")
    try:
        resources = TimeSeriesDataType.objects.filter(category=category)
        dates = {'base_date': date, 'end_date': date}
        date_obj = parser.parse(date)
        for resource in resources:
            for user_fb in UserFitbit.objects.filter(fitbit_user=fitbit_user):
                data = utils.get_fitbit_data(user_fb, resource, **dates)
                for datum in data:
                    # Create new record or update existing record
                    tsd, created = TimeSeriesData.objects.get_or_create(
                        user=user_fb.user, resource_type=resource,
                        date=date_obj)
                    tsd.value = datum['value'] if datum['value'] else None
                    tsd.save()
    except:
        logger.exception("Exception updating data")
        raise
    logger.debug("FITBIT DATA UPDATED")
