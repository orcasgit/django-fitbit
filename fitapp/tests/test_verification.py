"""
Tests in this file are for testing verification of fitbit subscriber endpoints.
https://dev.fitbit.com/docs/subscriptions/#verify-a-subscriber
"""

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings


class TestVerification(TestCase):
    """
    Class to test verification of Fitbit subscriber endpoints
    """

    def test_404(self):
        """
        Check various conditions that should result in a 404
        """
        # Empty non-GET requests
        resp = self.client.post(reverse('fitbit-update'))
        self.assertEqual(resp.status_code, 404)
        resp = self.client.put(reverse('fitbit-update'))
        self.assertEqual(resp.status_code, 404)

        # No code in settings or query string
        resp = self.client.get(reverse('fitbit-update'))
        self.assertEqual(resp.status_code, 404)

        # Code in query string, but not in settings
        resp = self.client.get(reverse('fitbit-update') + '?verify=code')
        self.assertEqual(resp.status_code, 404)

        with override_settings(FITAPP_VERIFICATION_CODE='VERIFICATION_CODE'):
            # Code in settings, but not query string
            resp = self.client.get(reverse('fitbit-update'))
            self.assertEqual(resp.status_code, 404)

            # Code in settings, wrong code in query string
            resp = self.client.get(reverse('fitbit-update') + '?verify=code')
            self.assertEqual(resp.status_code, 404)

    @override_settings(FITAPP_VERIFICATION_CODE='VERIFICATION_CODE')
    def test_verify(self):
        """
        Test the verification process. It consists of two GET requests:
        1. Contains a verify query param containing the verification code we
           have specified in the ``FITAPP_VERIFICATION_CODE`` setting. We
           should respond with a HTTP 204 code.
        2. Contains a verify query param containing a purposefully invalid
           verification code. We should respond with a 404
        """

        for verify, status in [('VERIFICATION_CODE', 204), ('BAD_CODE', 404)]:
            query_string = '?verify=' + verify
            resp = self.client.get(reverse('fitbit-update') + query_string)
            self.assertEqual(resp.status_code, status)
