import time

from sparrow.context.base_context import ValueContext
from sparrow.context.request_attacher import RequestAttacher

START_TIME_KEY = "START_TIME"


class StartTimeContext(ValueContext, RequestAttacher):
    stats_key = START_TIME_KEY
    auto_attach = True
    attach_priority = 0

    @classmethod
    def attach_from_request(cls, request, **kwargs):
        cls.set(time.time())
