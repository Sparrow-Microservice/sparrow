import logging
from flask import signals
from wish_flask.log.meta import LoggingMixin


CONTEXT_KEY = 'WISH_CONTEXT'


class EmptyDict(dict, LoggingMixin):
    # pylint: disable=unused-argument
    def get(self, k, d=None):
        return d

    # pylint: disable=unused-argument
    def __setitem__(self, i, y):
        self.logger.warning('Setting to EmptyDict has no effect! (%s:%s)', i, y)

    # pylint: disable=unused-argument
    def setdefault(self, k, d=None):
        return d


EMPTY_DICT = EmptyDict()
_logger = logging.getLogger(__name__)


class BaseContext(object):
    # possible values: threading.local(), flask.g, flask.request
    FLASK_CONTEXT = None

    @classmethod
    def get_context_dict(cls, init=False):
        # bool(cls.FLASK_CONTEXT) should be True for threading.local(),
        # while it should be False for flask.g if not in flask context.
        if not cls.FLASK_CONTEXT:
            return EMPTY_DICT
        if init and not hasattr(cls.FLASK_CONTEXT, CONTEXT_KEY):
            setattr(cls.FLASK_CONTEXT, CONTEXT_KEY, {})
        context = getattr(cls.FLASK_CONTEXT, CONTEXT_KEY, EMPTY_DICT)
        return context

    @classmethod
    def get_context(cls, key, default=None):
        context = cls.get_context_dict(init=False)
        return context.get(key, default)

    @classmethod
    def set_context(cls, key, value):
        context = cls.get_context_dict(init=True)
        context[key] = value

    @classmethod
    def clean_context(cls, *args):
        try:
            if cls.FLASK_CONTEXT and hasattr(cls.FLASK_CONTEXT, CONTEXT_KEY):
                if hasattr(cls.FLASK_CONTEXT, 'pop'):
                    # For flask.g flask.request
                    cls.FLASK_CONTEXT.pop(CONTEXT_KEY, None)
                else:
                    # For local()
                    delattr(cls.FLASK_CONTEXT, CONTEXT_KEY)
        except Exception as e:
            _logger.warning('Clean context failed: %s', str(e))


class BaseRequestContext(BaseContext):

    @classmethod
    def set_context_to_flask_request(cls):
        from flask import request
        cls.FLASK_CONTEXT = request

    @classmethod
    def set_context_to_threading_local(cls, app=None):
        # !!!Please remember to call clean_context if thread/greenlet pool is used.
        from threading import local
        cls.FLASK_CONTEXT = local()
        kwargs = {}
        if app:
            kwargs['sender'] = app
        signals.request_started.connect(cls.clean_context, **kwargs)


class ValueContext(BaseRequestContext):
    stats_key = None

    @classmethod
    def get(cls, default=None):
        return cls.get_context(cls.stats_key, default=default)

    @classmethod
    def set(cls, value):
        return cls.set_context(cls.stats_key, value)
