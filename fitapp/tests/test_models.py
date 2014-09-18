from fitapp.models import UserFitbit, TimeSeriesDataType

from .base import FitappTestBase


class TestFitappModels(FitappTestBase):
    def test_userfitbit(self):
        """ UserFitbit was already created in base, now test the properties """
        self.assertEqual(self.fbuser.user, self.user)
        self.assertEqual(self.fbuser.__str__(), self.username)
        self.assertEqual(self.fbuser.get_user_data(), {
            'resource_owner_key': self.fbuser.auth_token,
            'resource_owner_secret': self.fbuser.auth_secret,
            'user_id': self.fbuser.fitbit_user
        })

    def test_timeseriesdatatype(self):
        """ TimeSeriesDataTypes are created via fixtures. """
        self.assertEqual(TimeSeriesDataType.objects.count(), 36)
        assert hasattr(TimeSeriesDataType, 'activities')
        assert hasattr(TimeSeriesDataType, 'body')
        assert hasattr(TimeSeriesDataType, 'sleep')
        assert hasattr(TimeSeriesDataType, 'foods')
        self.assertEqual(str(TimeSeriesDataType.objects.get(resource='steps')),
                         'activities/steps')
