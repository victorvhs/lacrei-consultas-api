from rest_framework.test import APITestCase


class ThrottlesTest(APITestCase):
    def test_throttle_classes_exist(self):
        from core.throttles import AuthRateThrottle, SharedAnonThrottle, SharedUserThrottle

        self.assertEqual(SharedAnonThrottle.rate, "20/min")
        self.assertEqual(SharedUserThrottle.rate, "300/min")
        self.assertEqual(AuthRateThrottle.rate, "5/min")
