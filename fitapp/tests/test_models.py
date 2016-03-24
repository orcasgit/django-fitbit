from fitapp.models import TimeSeriesDataType
from django.db import IntegrityError

from .base import FitappTestBase


class TestFitappModels(FitappTestBase):
    def test_userfitbit(self):
        """ UserFitbit was already created in base, now test the properties """
        self.assertEqual(self.fbuser.user, self.user)
        self.assertEqual(self.fbuser.__str__(), self.username)
        self.assertEqual(self.fbuser.get_user_data(), {
            'access_token': self.fbuser.access_token,
            'refresh_token': self.fbuser.refresh_token,
            'user_id': self.fbuser.fitbit_user
        })

        # Trying to create another UserFitbit with the same fitbit_user should
        # result in an IntegrityError
        user2 = self.create_user(
            username='%s2' % self.username, password=self.password)
        self.assertRaises(IntegrityError, self.create_userfitbit,
                          user=user2, fitbit_user=self.fbuser.fitbit_user)

    def test_timeseriesdatatype(self):
        """ TimeSeriesDataTypes are created via fixtures. """
        self.assertEqual(TimeSeriesDataType.objects.count(), 36)
        assert hasattr(TimeSeriesDataType, 'activities')
        assert hasattr(TimeSeriesDataType, 'body')
        assert hasattr(TimeSeriesDataType, 'sleep')
        assert hasattr(TimeSeriesDataType, 'foods')
        self.assertEqual(str(TimeSeriesDataType.objects.get(resource='steps')),
                         'activities/steps')
