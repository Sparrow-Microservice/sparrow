# -*- coding: utf-8 -*-
import logging
import traceback
import os
import typing as t

from flask import request

from wish_flask.exceptions.errors import Errors
from wish_flask.log.meta import LoggingMixin
from wish_flask.monitor.metrics import METRIC_EXCEPTIONS
from wish_flask.context.user_id_context import UserIdContext
from wish_flask.log.request_log import LogRequestHelper
from wish_flask.utils.attr_utils import set_attr_from_config


class BaseExceptionHandler(LoggingMixin):

    def __init__(self,
                 log_request: LogRequestHelper,
                 log_body=True,
                 log_trace=True,
                 td_logger: t.Union[str, logging.Logger, None] = None,
                 app=None
                 ):
        self.log_request = log_request
        self.log_body = log_body
        self.log_trace = log_trace
        self.td_logger = td_logger
        self.post_init()
        if app:
            self.init_app(app)

    def init_app(self, app):
        config = app.config.get('log_exception', {})
        set_attr_from_config(self, config, 'log_body')
        set_attr_from_config(self, config, 'log_trace')
        set_attr_from_config(self, config, 'td_logger')
        self.post_init()

    def post_init(self):
        if isinstance(self.td_logger, str):
            self.td_logger = logging.getLogger(self.td_logger)

    def handle_exception(self, error):
        raise NotImplementedError

    @classmethod
    def error_message(cls, error):
        return str(error)

    @classmethod
    def error_code(cls, error):
        return Errors.UNKNOWN

    @classmethod
    def error_extra_data(cls, error) -> t.Union[str, None]:
        return None

    @classmethod
    def error_traceback(cls, error, tb=None):
        tb = tb or error.__traceback__
        return ''.join(traceback.format_exception(type(error), error, tb))

    @classmethod
    def response_http_code(cls, rsp):
        return rsp[1] if rsp and isinstance(rsp, tuple) and len(rsp) > 1 and isinstance(rsp[1], int) else None

    def log_to_console(self, error, tb=None, rsp=None, log_trace=None, log_body=None):
        log_trace = log_trace if log_trace is not None else self.log_trace
        log_body = log_body if log_body is not None else self.log_body

        self.logger.error(
            os.linesep.join([
                '',
                '%s: %s',  # Exception
                'ErrCode: %s',
                '%s %s',  # Uri
                'Body: %s',
                'Data: %s',
                'HttpCode: %s',
                'Trace: %s',
            ]), type(error).__name__, self.error_message(error) or '',
            self.error_code(error),
            self.log_request.method() or 'Method', self.log_request.full_path() or 'Uri',
            self.log_request.body_text() if log_body else '(Skipped)',
            self.error_extra_data(error),
            self.response_http_code(rsp),
            self.error_traceback(error, tb=tb) if log_trace else '(Skipped)'
        )

    def log_to_td(self, error, tb=None, rsp=None, log_trace=None, log_body=None):
        if not self.td_logger:
            return
        log_trace = log_trace if log_trace is not None else self.log_trace
        log_body = log_body if log_body is not None else self.log_body
        data = {
            'uri': self.log_request.path(),
            'rule': self.log_request.rule(),
            'query': self.log_request.query_string(),
            'method': self.log_request.method(),
            'http_code': self.response_http_code(rsp),
            'request_body': self.log_request.body_text() if log_body else '(Skipped)',
            'traceback': self.error_traceback(error, tb=tb) if log_trace else '(Skipped)',
            'exp': type(error).__name__,
            'err_code': self.error_code(error),
            'exp_msg': self.error_message(error),
            'forwarded_ip': request.headers.get('X-Forwarded-For'),
            'remote_addr': request.headers.environ.get('REMOTE_ADDR'),
            'extra_data': self.error_extra_data(error)
        }
        self.td_logger.info(data)

    def log_to_metrics(self, error, rsp=None):
        METRIC_EXCEPTIONS.inc(
            exp=type(error).__name__,
            err_code=self.error_code(error) or '',
            uri=self.log_request.path() or '',  # TODO: Maybe we should record uri rule in metrics.
            http_code=self.response_http_code(rsp) or ''
        )

    def _get_error_extra_data_for_sentry(self):
        params = self.log_request.args()
        header = self.log_request.header()
        cookies = self.log_request.cookie()
        extra_data = {
            'method': self.log_request.method(),
            'params': params,
            'header': header,
            'cookies': cookies,
        }
        return extra_data

    def config_sentry(self):
        extra_data = self._get_error_extra_data_for_sentry()

        user_id = UserIdContext.get('-')
        user = {
            'id': user_id,
        }

        tags = {
            'uri': self.log_request.full_path(),
            'full_uri': self.log_request.url(),
        }

        import sentry_sdk
        with sentry_sdk.configure_scope() as scope:
            for key, value in tags.items():
                scope.set_tag(key, value)
            scope.user = user
            for key, value in extra_data.items():
                scope.set_extra(key, value)
