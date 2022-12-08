import typing as t

from werkzeug.exceptions import BadRequest
from werkzeug.wrappers import Request as RequestBase
from werkzeug.wrappers import Response as ResponseBase


class Request(RequestBase):
    pass


class Response(ResponseBase):
    pass
