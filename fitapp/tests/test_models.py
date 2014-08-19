from fitapp.models import UserFitbit

from .base import FitappTestBase


class TestFitappModels(FitappTestBase):
    def test_userfitbit(self):
        """ UserFitbit was already created in base, now test the properties """
        self.assertEqual(self.fbuser.user, self.user)
        self.assertEqual(self.fbuser.__str__(), self.username)
        self.assertEqual(self.fbuser.get_user_data(), {
            'user_key': self.fbuser.auth_token,
            'user_secret': self.fbuser.auth_secret,
            'user_id': self.fbuser.fitbit_user
        })
