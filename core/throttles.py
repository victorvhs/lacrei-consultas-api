from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class SharedAnonThrottle(AnonRateThrottle):
    rate = "20/min"


class SharedUserThrottle(UserRateThrottle):
    rate = "300/min"


class AuthRateThrottle(AnonRateThrottle):
    rate = "5/min"
