import random

from sparrow.context.base_context import ValueContext
from sparrow.context.request_attacher import RequestAttacher
from sparrow.context.utils import expend_headers, get_header_value

REQUEST_ID_KEY = 'REQUEST_ID'
REQUEST_ID_HEADERS = expend_headers('Wish-Request-Id')

REQUEST_CLIENT_DEFAULT_Value = 'DEFAULT'
REQUEST_CLIENT_ID_KEY = 'REQUEST_CLIENT_ID'
REQUEST_ID_CLIENT_HEADERS = expend_headers('Wish-Request-Client-Id')

REQUEST_ID_RSP_HEADER = 'Wish-RequestId'  # Use a different key for rsp to avoid hacking

REQUEST_TRACING_ID_KEY = 'REQUEST_TRACING_ID'
REQUEST_TRACING_ID_HEADERS = expend_headers('Wish-Request-Tracing-Id')
REQUEST_TRACING_ID_RSP_HEADER = 'Wish-RequestTracingId'  # Use a different key for rsp to avoid hacking


class RequestIdContext(ValueContext, RequestAttacher):
    stats_key = REQUEST_ID_KEY
    auto_attach = True

    @classmethod
    def attach_from_request(cls, request, **kwargs):
        # set request id in context for logging
        request_id = get_header_value(request.headers, REQUEST_ID_HEADERS, "%08x" % random.getrandbits(32))
        cls.set(request_id)


# Ensure that RequestTracingIdContext is defined after RequestIdContext,
# so RequestTracingIdContext is attached after RequestIdContext.
class RequestTracingIdContext(ValueContext, RequestAttacher):
    stats_key = REQUEST_TRACING_ID_KEY
    auto_attach = True

    @classmethod
    def attach_from_request(cls, request, **kwargs):
        request_tracing_id = get_header_value(request.headers, REQUEST_TRACING_ID_HEADERS, RequestIdContext.get())
        if request_tracing_id:
            cls.set(request_tracing_id)


class RequestClientIdContext(ValueContext, RequestAttacher):
    stats_key = REQUEST_CLIENT_ID_KEY
    auto_attach = True

    @classmethod
    def set_client_id(cls, client_id, override=False):
        if not client_id:
            return None
        if not override and cls.get():
            # We have already set client id from request headers.
            return None
        client_id = str(client_id)
        cls.set(client_id)
        # set client id
        RequestClientIdContext.set(client_id)

    @classmethod
    def attach_from_request(cls, request, **kwargs):
        client_id = get_header_value(request.headers, REQUEST_ID_CLIENT_HEADERS, REQUEST_CLIENT_DEFAULT_Value)
        if client_id:
            cls.set(client_id)
            RequestClientIdContext.set(client_id)
