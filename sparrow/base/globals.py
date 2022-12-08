from werkzeug.local import LocalProxy
from contextvars import ContextVar
import typing as t

if t.TYPE_CHECKING:  # pragma: no cover
    from .app import Flask
    from .ctx import _AppCtxGlobals
    from .ctx import AppContext
    from .ctx import RequestContext
    from .wrappers import Request

_cv_app: ContextVar["AppContext"] = ContextVar("flask.app_ctx")
_cv_request: ContextVar["RequestContext"] = ContextVar("flask.request_ctx")
_no_req_msg = """\
Working outside of request context.

This typically means that you attempted to use functionality that needed
an active HTTP request. Consult the documentation on testing for
information about how to avoid this problem.\
"""
request_ctx: "RequestContext" = LocalProxy(  # type: ignore[assignment]
    _cv_request, unbound_message=_no_req_msg
)


_no_app_msg = """\
Working outside of application context.

This typically means that you attempted to use functionality that needed
the current application. To solve this, set up an application context
with app.app_context(). See the documentation for more information.\
"""
current_app: "Flask" = LocalProxy(  # type: ignore[assignment]
    _cv_app, "app", unbound_message=_no_app_msg
)

request: "Request" = LocalProxy(  # type: ignore[assignment]
    _cv_request, "request", unbound_message=_no_req_msg
)