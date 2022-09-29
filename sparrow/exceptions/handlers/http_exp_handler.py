# -*- coding: utf-8 -*-
from sparrow.base.schema import Rsp

try:
    from marshmallow import ValidationError
except:
    ValidationError = None
from werkzeug.exceptions import HTTPException, InternalServerError

from sparrow.exceptions.errors import Errors
from sparrow.exceptions.handlers.base_exp_hander import BaseExceptionHandler
from sparrow.i18n import _

from flask.signals import got_request_exception


class HttpExceptionHandler(BaseExceptionHandler):

    def handle_exception(self, error):
        assert isinstance(error, HTTPException), 'error is not HTTPException'
        rsp = self.get_response(error)
        self.log_to_console(error, rsp=rsp)
        self.log_to_td(error, rsp=rsp)
        self.log_to_metrics(error, rsp=rsp)
        got_request_exception.send(self, exception=error)
        return rsp

    @classmethod
    def error_code(cls, error):
        return error.code

    @classmethod
    def get_response(cls, error):
        """Return a JSON response containing a description of the error

        This method is registered at app init to handle ``HTTPException``.

        - When ``abort`` is called in the code, an ``HTTPException`` is
          triggered and Flask calls this handler.

        - When an exception is not caught in a view, Flask makes it an
          ``InternalServerError`` and calls this handler.

        flask-smorest republishes webargs's
        :func:`abort <webargs.flaskparser.abort>`. This ``abort`` allows the
        caller to pass kwargs and stores them in ``exception.data`` so that the
        error handler can use them to populate the response payload.

        Extra information expected by this handler:

        - `message` (``str``): a comment
        - `errors` (``dict``): errors, typically validation errors in
            parameters and request body
        - `headers` (``dict``): additional headers
        """
        headers = {}
        payload = getattr(error, 'payload', None) or Rsp(code=cls.error_code(error), msg=_(error.name)).to_dict()

        # Get additional info passed as kwargs when calling abort
        # data may not exist if HTTPException was raised without webargs abort
        data = getattr(error, 'data', None)
        if data and isinstance(data, dict):
            payload_data = {}
            # If we passed a custom message
            if 'message' in data:
                payload_data['message'] = data['message']
            # If we passed "errors"
            if 'errors' in data:
                payload_data['errors'] = data['errors']
            # If webargs added validation errors as "messages"
            # (you should use 'errors' as it is more explicit)
            elif 'messages' in data:
                payload_data['errors'] = data['messages']
            # If we passed additional headers
            if 'headers' in data:
                headers = data['headers']

            if payload_data and isinstance(payload, dict):
                payload['data'] = payload_data

        return payload, error.code, headers


class InternalServerErrorHandler(HttpExceptionHandler):

    @classmethod
    def error_code(cls, error):
        return Errors.UNKNOWN

    def handle_exception(self, error):
        assert isinstance(error, InternalServerError), 'error is not InternalServerError'

        rsp = self.get_response(error)
        orig_exp = error.original_exception or error
        self.log_to_console(orig_exp, rsp=rsp)
        self.log_to_td(orig_exp, rsp=rsp)
        self.log_to_metrics(orig_exp, rsp=rsp)
        got_request_exception.send(self, exception=orig_exp)
        return rsp


class UnprocessableEntityHandler(HttpExceptionHandler):
    @classmethod
    def error_code(cls, error):
        return Errors.VALIDATE_FAILED

    @classmethod
    def error_traceback(cls, error, tb=None):
        error_context = error.__context__
        if error_context and ValidationError and isinstance(error_context, ValidationError):
            error = error_context
            tb = error_context.__traceback__
        return super().error_traceback(error, tb=tb)


class NotFoundHandler(HttpExceptionHandler):

    @classmethod
    def error_code(cls, error):
        return Errors.NOT_FOUND

    @classmethod
    def get_response(cls, error):
        return Rsp(
            code=cls.error_code(error),
            msg=_('You are reaching a non-existing place!')
        ).to_dict(), error.code
