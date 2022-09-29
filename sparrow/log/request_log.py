import re
import functools
from flask import request
from werkzeug._compat import to_unicode

from sparrow.context.cache_context import CacheContext
from sparrow.utils.attr_utils import set_attr_from_config


class RequestCache(object):
    MISSING = object()

    @classmethod
    def cache(cls, fn):
        key = fn.__name__
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            cache_value = cls.get(key)
            if cache_value is not cls.MISSING:
                return cache_value
            value = fn(*args, **kwargs)
            cls.set(key, value)
            return value
        return wrapper

    @classmethod
    def get(cls, key):
        return CacheContext.get({}).get(key, cls.MISSING)

    @classmethod
    def set(cls, key, value):
        cache = CacheContext.get({})
        cache[key] = value
        CacheContext.set(cache)


class LogRequestHelper(object):

    MAX_SIZE_BODY = 1 << 12

    def __init__(self, body_limit=None, body_patterns=None):
        self.body_limit = body_limit or self.MAX_SIZE_BODY
        self.body_patterns = body_patterns or []

    def init_app(self, app):
        config = app.config.get('log_request', {})
        set_attr_from_config(self, config, 'body_limit')
        set_attr_from_config(self, config, 'body_patterns')

    @classmethod
    def _limit_text(cls, text, size):
        if not text:
            return text
        if not size or size < 0:
            return text
        body_len = len(text)
        if body_len > size:
            text = text[:size] + ('...[Len:%s]' % body_len)
        return text

    def _get_body_text(self):
        request_body = None
        if request:
            try:
                if request.mimetype != 'multipart/form-data':
                    request_body = request.get_data(as_text=True)
            except:
                pass
        request_body = self._limit_text(request_body, self.body_limit)
        return request_body

    def _apply_pattern_for_body(self, request_body):
        if request_body:
            for p in self.body_patterns:
                try:
                    request_body = re.sub(p, r'\1***', request_body)
                except:
                    pass
        return request_body

    @RequestCache.cache
    def body_text(self):
        request_body = self._get_body_text()
        return self._apply_pattern_for_body(request_body)

    @classmethod
    def full_path(cls):
        return request.full_path.rstrip('?') if request else None

    @classmethod
    def url(cls):
        return request.url if request else None

    @classmethod
    def path(cls):
        return request.path if request else None

    @classmethod
    def query_string(cls):
        return to_unicode(request.query_string, request.url_charset) if request else None

    @classmethod
    def method(cls):
        return request.method if request else None

    @classmethod
    def cookie(cls):
        return request.cookies.to_dict() if request and request.cookies else {}

    @classmethod
    def args(cls):
        return request.args.to_dict() if request and request.args else {}

    @classmethod
    def header(cls):
        return dict(request.headers) if request and request.headers else {}

    @classmethod
    def rule(cls):
        return request.url_rule.rule if request and request.url_rule else None

    @classmethod
    def scheme(cls):
        return request.scheme if request else None

    @classmethod
    def remote_addr(cls):
        return request.remote_addr if request else None

    @classmethod
    def real_remote_addr(cls):
        if request:
            return request.headers.get('X-Forwarded-For') or request.remote_addr
        return None
