# -*- coding: utf-8 -*-
from werkzeug.exceptions import BadRequest, InternalServerError
import typing

from werkzeug.http import HTTP_STATUS_CODES

from wish_flask.lib.py_enum import PyEnumMixin
from wish_flask.micro.utils import is_micro_api
from wish_flask.i18n import _


class PropagateEnum(PyEnumMixin):
    THROUGHOUT = 'throughout'
    INTERNAL = 'internal'
    ONCE = 'once'
    OFF = 'off'


class BaseApiException(Exception):
    def __init__(self,
                 code: int,
                 msg: str = '',
                 data: typing.Any = None,
                 headers: dict = None,
                 **kwargs):
        self.code = code
        self.msg = msg.format(**kwargs) if '{' in msg and '}' in msg else msg
        self.data = data
        self.headers = headers or {}
        self.kwargs = kwargs
        self.status_code = BadRequest.code
        self.propagate = None
        super().__init__(self.msg)

        self.init()
        self.add_propagate_header()

    def init(self):
        pass

    def add_propagate_header(self):
        if self.propagate:
            self.headers['propagate'] = self.propagate

    def get_payload(self):
        payload = {
            'code': self.code,
            'msg': self.msg
        }
        if self.data:
            payload['data'] = self.data
        return payload

    def send_request_exception_signals_switch(self):
        """
        Now request_exception signals will be caught by apm and sentry
        """
        raise NotImplementedError

    def __str__(self):
        return self.msg

    def __repr__(self):
        return type(self).__name__ + str((self.code, self.msg))


class ApiException(BaseApiException):
    """
    Api exception that will be propagated to user endpoint.
    """

    def init(self):
        self.propagate = PropagateEnum.THROUGHOUT

    def send_request_exception_signals_switch(self):
        return False


class InternalApiException(BaseApiException):
    """
    Api exception that will only be propagated in all internal micro servers.
    """

    def init(self):
        self.propagate = PropagateEnum.INTERNAL

    def get_payload(self):
        if not is_micro_api():
            return {
                'code': self.code,
                'msg': HTTP_STATUS_CODES.get(InternalServerError.code) or _('Unknown Error')
            }
        return super().get_payload()

    def send_request_exception_signals_switch(self):
        return True


class AdjacentApiException(BaseApiException):
    """
    Api exception that will only be propagated to the calling internal server.
    """

    def init(self):
        self.propagate = PropagateEnum.ONCE

    def get_payload(self):
        if not is_micro_api():
            return {
                'code': self.code,
                'msg': HTTP_STATUS_CODES.get(InternalServerError.code) or _('Unknown Error')
            }
        return super().get_payload()

    def send_request_exception_signals_switch(self):
        return True


class StandaloneApiException(BaseApiException):
    """
    Api exception that will not be propagated outside of this server.
    Http code of 500 will be returned.
    """

    def init(self):
        self.status_code = InternalServerError.code
        self.propagate = PropagateEnum.OFF

    def get_payload(self):
        return {
            'code': self.code,
            'msg': HTTP_STATUS_CODES.get(InternalServerError.code) or _('Unknown Error')
        }

    def send_request_exception_signals_switch(self):
        return True
