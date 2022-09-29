# -*- coding: utf-8 -*-
from flask.signals import got_request_exception
from wish_flask.exceptions.api_exception import BaseApiException, ApiException
from wish_flask.exceptions.handlers.base_exp_hander import BaseExceptionHandler
from wish_flask.monitor.metrics import METRIC_EXCEPTIONS


class BaseApiExceptionHandler(BaseExceptionHandler):

    def handle_exception(self, error):
        assert isinstance(error, BaseApiException), 'error is not BaseApiException'
        rsp = self.get_response(error)
        self.log_to_console(error, rsp=rsp)
        self.log_to_td(error, rsp=rsp)
        self.log_to_metrics(error, rsp=rsp)

        if error.send_request_exception_signals_switch():
            got_request_exception.send(self, exception=error)
        return rsp

    @classmethod
    def get_response(cls, error):
        payload = error.get_payload()
        headers = error.headers or {}
        return payload, error.status_code, headers

    def log_to_metrics(self, error, rsp=None):
        METRIC_EXCEPTIONS.inc(
            exp=type(error).__name__,
            err_code=self.error_code(error) or '',
            api_exp=isinstance(error, ApiException),
            uri=self.log_request.path() or '',  # TODO: Maybe we should record uri rule in metrics.
            http_code=error.status_code
        )

    @classmethod
    def error_code(cls, error):
        return error.code

    @classmethod
    def error_extra_data(cls, error):
        return error.data
