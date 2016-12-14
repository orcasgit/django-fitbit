from fitapp.models import UserFitbit
from fitapp.templatetags import fitbit

from .base import FitappTestBase


class TestFitappTemplatetags(FitappTestBase):

    def test_is_integrated_with_fitbit(self):
        """Users with stored OAuth information are integrated."""
        self.assertTrue(fitbit.is_integrated_with_fitbit(self.user))

    def test_is_not_integrated_with_fitbit(self):
        """User is not integrated if we have no OAuth data for them"""
        UserFitbit.objects.all().delete()
        self.assertFalse(fitbit.is_integrated_with_fitbit(self.user))
