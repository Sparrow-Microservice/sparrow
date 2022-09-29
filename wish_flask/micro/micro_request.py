from wish_flask.base.request import EasyRequest
from wish_flask.context.locale_context import LocaleContext


class MicroRequest(EasyRequest):

    timeout = 20

    @classmethod
    def apply_accept_language(cls, kwargs):
        # Set Accept-Language
        headers = kwargs.get('headers', {})
        lang = headers.get('Accept-Language')
        if not lang:
            loc = LocaleContext.get()
            if loc:
                headers['Accept-Language'] = LocaleContext.get()
        kwargs['headers'] = headers

    @classmethod
    def apply_timeout(cls, kwargs):
        if cls.timeout is not None:
            timeout = kwargs.get('timeout')
            if timeout is None:
                kwargs['timeout'] = cls.timeout

    @classmethod
    def request(cls, method, url, **kwargs):
        cls.apply_accept_language(kwargs)
        cls.apply_timeout(kwargs)
        return super(MicroRequest, cls).request(method, url, **kwargs)
