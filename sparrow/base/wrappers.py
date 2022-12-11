import typing as t

from werkzeug.exceptions import BadRequest
from werkzeug.wrappers import Request as RequestBase
from werkzeug.wrappers import Response as ResponseBase

if t.TYPE_CHECKING:  # pragma: no cover
    from werkzeug.routing import Rule


class Request(RequestBase):
    url_rule: t.Optional["Rule"] = None

    view_args: t.Optional[t.Dict[str, t.Any]] = None


class Response(ResponseBase):
    pass
