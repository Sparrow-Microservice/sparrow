# -*- coding: utf-8 -*-
import functools
import time

from flask import Flask, request
from werkzeug.exceptions import InternalServerError, NotFound

from sparrow.base.pubsub import PubSubManager
from sparrow.base.resource import ResourceRegister
from sparrow.base.view import ViewFilterChain
from sparrow.blueprints.general import general_bp
from sparrow.exceptions.handlers.base_exp_hander import BaseExceptionHandler
from sparrow.log.request_log import LogRequestHelper
from sparrow.micro.view_filter import MicroViewFilter
from sparrow.context.request_attacher import RequestAttachRegister
from sparrow.context.base_context import BaseRequestContext
from sparrow.context.request_id_context import RequestTracingIdContext, REQUEST_TRACING_ID_RSP_HEADER, \
    RequestIdContext, REQUEST_ID_RSP_HEADER
from sparrow.context.start_time_context import StartTimeContext
from sparrow.exceptions.api_exception import BaseApiException
from sparrow.exceptions.handlers.api_exp_handler import BaseApiExceptionHandler
from sparrow.exceptions.handlers.http_exp_handler import InternalServerErrorHandler, NotFoundHandler
from sparrow.utils.import_utils import import_submodules
from sparrow.extensions.connector import Connector
from sparrow.log.meta import LoggingMixin
from sparrow.extensions.cache_manager.connect import CacheManagerConnector
from sparrow.i18n.wish_babel import WishBabel
from sparrow.extensions.sentry.instance import sentry_switch
from sparrow.lib.json_encoder import WishJSONEncoder
from sparrow.base.request import EasyRequest
from sparrow.utils.request_utils import hit_log_request


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType
    from typing import List, Union


class WishFlaskApplication(LoggingMixin, Flask):

    SLOW_REQUEST_THRESHOLD = 750

    def __init__(self,
                 name: str,
                 import_modules: 'List[Union[ModuleType, str]]' = None,
                 *args,
                 **kwargs):
        """WishFlaskApplication

        :param name: The name of the application package.
        :param import_modules: A list of strings or modules.
            All listed modules will be automatically imported for resource collection.
        :param args: flask args
        :param kwargs: flask kwargs
        """
        self.import_modules = import_modules or []
        self.td_exception_logger = None
        self.view_filter_chain = ViewFilterChain()
        self.babel = None
        self.log_request = LogRequestHelper()
        self.pubsub_manager = PubSubManager()
        super(WishFlaskApplication, self).__init__(name, *args, **kwargs)


        self.before_close_funcs = []
        self.before_kill_funcs = []


        self.setups()

    def log_exception(self, exc_info):
        # This will be called when exceptions are not handled by registered error handlers,
        # or when new error raised in handlers. Detailed exception will be logged in InternalServerErrorHandler.
        self.logger.warn('Server error exception occurred: %s', repr(exc_info[1]))

    def add_url_rule(
        self,
        rule,
        endpoint=None,
        view_func=None,
        **kwargs
    ):
        target_view_func = view_func
        if view_func:
            @functools.wraps(view_func)
            def target_view_func(*args, **kwargs):
                return self.view_filter_chain.process_chain(view_func, args, kwargs)
        return super().add_url_rule(rule, endpoint=endpoint, view_func=target_view_func, **kwargs)

    def setups(self):
        # Called before loading config
        BaseRequestContext.set_context_to_threading_local(app=self)
        self.before_request(self._cache_request_data)
        self.before_request(self._attach_contexts)
        self.after_request(self._log_request)
        self.after_request(self._attach_headers)

        self.view_filter_chain.add_filter(MicroViewFilter())

        self._register_buildin_bps()

    @classmethod
    def _cache_request_data(cls):
        if request.mimetype in ['application/x-www-form-urlencoded', 'application/x-url-encoded']:
            # Cache raw data before parsing for form-urlencoded type explicitly so we can log it.
            request.get_data()

    @classmethod
    def _attach_contexts(cls):
        RequestAttachRegister.do_auto_attach(request)

    def _log_request(self, resp):
        if not hit_log_request():
            return resp
        curtime = time.time()
        operation_time = (curtime - StartTimeContext.get(curtime)) * 1000.0
        slow_warning = '(SLOW) ' if operation_time > self.SLOW_REQUEST_THRESHOLD else ''
        self.logger.info('%s%dms %s %s %s %s %s',
                         slow_warning, operation_time,
                         self.log_request.real_remote_addr(),
                         self.log_request.method(),
                         self.log_request.scheme(),
                         self.log_request.full_path(),
                         resp.status)
        return resp

    def _attach_headers(self, resp):
        resp.headers.set(REQUEST_ID_RSP_HEADER, RequestIdContext.get(''))
        resp.headers.set(REQUEST_TRACING_ID_RSP_HEADER, RequestTracingIdContext.get(''))
        return resp

    def init(self):
        # Called after loading config
        self.pre_init()
        self.do_init()
        self.post_init()

    def pre_init(self):
        self._init_easy_request()
        self._init_log_request()
        self._init_pubsub()
        self._register_error_handlers()

    def do_init(self):
        self.init_i18n()
        self.load_modules()
        self.connect()
        self.init_resources()

    def post_init(self):
        # Check cache manager instances
        CacheManagerConnector.instance_check()

        # setup sentry
        if sentry_switch:
            self.before_request(BaseExceptionHandler(self.log_request, app=self).config_sentry)

        # Start pubsub threads
        self.pubsub_manager.consume()

    def load_modules(self):
        for m in self.import_modules:
            import_submodules(m)

    def connect(self):
        self.connect_extensions()

    def connect_extensions(self):
        Connector.connect_all(self)

    def init_resources(self):
        ResourceRegister.do_init_all(self)

    def init_i18n(self):
        self.babel = WishBabel(self)

    def _init_easy_request(self):
        EasyRequest.init(app=self)

    def _init_log_request(self):
        self.log_request.init_app(self)

    def _init_pubsub(self):
        self.pubsub_manager.init_app(self)

    def _register_error_handlers(self):
        self.register_error_handler(
            BaseApiException,
            BaseApiExceptionHandler(self.log_request, app=self).handle_exception
        )
        self.register_error_handler(
            InternalServerError,
            InternalServerErrorHandler(self.log_request, app=self).handle_exception
        )
        self.register_error_handler(
            NotFound,
            NotFoundHandler(self.log_request, app=self).handle_exception
        )

    def _register_buildin_bps(self):
        self.register_blueprint(general_bp)

    def _set_json_encoder(self):
        # Currently not used
        self.json_encoder = WishJSONEncoder

    def before_close(self, f):
        """Registers a function to run before the application is close gracefully.
        """
        self.before_close_funcs.append(f)
        return f

    def before_kill(self, f):
        """ Registers a function to run before the application is killed.
        """
        self.before_kill_funcs.append(f)
        return f

    def close(self):
        self.logger.info("Wish flask application is closing.")
        try:
            for func in self.before_close_funcs:
                func()
            ResourceRegister.close()
        except Exception as e:
            self.logger.warning(
                "Wish flask application close gracefully failed, err: %s. Next step will run all kill function.",
                str(e))
            self.kill()

    def kill(self):
        for func in self.before_kill_funcs:
            func()
