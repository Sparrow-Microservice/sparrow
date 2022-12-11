import contextvars
import typing as t
from types import TracebackType

from .globals import _cv_app
from .globals import _cv_request

if t.TYPE_CHECKING:  # pragma: no cover
    from .app import Sparrow
    from .wrappers import Request


class AppContext:
    """The app context contains application-specific information. An app
    context is created and pushed at the beginning of each request if
    one is not already active. An app context is also pushed when
    running CLI commands.
    """

    def __init__(self, app: "Sparrow") -> None:
        self.app = app
        self._cv_tokens: t.List[contextvars.Token] = []

    def push(self) -> None:
        """Binds the app context to the current context."""
        self._cv_tokens.append(_cv_app.set(self))

    def pop(self, exc: t.Optional[BaseException] = None) -> None:  # type: ignore
        ctx = _cv_app.get()
        _cv_app.reset(self._cv_tokens.pop())

        if ctx is not self:
            raise AssertionError(
                f"Popped wrong app context. ({ctx!r} instead of {self!r})"
            )

    def __enter__(self) -> "AppContext":
        self.push()
        return self

    def __exit__(
            self,
            exc_type: t.Optional[type],
            exc_value: t.Optional[BaseException],
            tb: t.Optional[TracebackType],
    ) -> None:
        self.pop(exc_value)


class RequestContext:
    """The request context contains per-request information. The Flask
    app creates and pushes it at the beginning of the request, then pops
    it at the end of the request. It will create the URL adapter and
    request object for the WSGI environment provided.

    Do not attempt to use this class directly, instead use
    :meth:`~flask.Flask.test_request_context` and
    :meth:`~flask.Flask.request_context` to create this object.

    When the request context is popped, it will evaluate all the
    functions registered on the application for teardown execution
    (:meth:`~flask.Flask.teardown_request`).

    The request context is automatically popped at the end of the
    request. When using the interactive debugger, the context will be
    restored so ``request`` is still accessible. Similarly, the test
    client can preserve the context after the request ends. However,
    teardown functions may already have closed some resources such as
    database connections.
    """

    def __init__(
            self,
            app: "Sparrow",
            environ: dict,
            request: t.Optional["Request"] = None,
    ) -> None:
        self.app = app

        if request is None:
            request = app.request_class(environ)

        self.request: Request = request
        self.url_adapter = app.create_url_adapter(self.request)

        self._cv_tokens: t.List[t.Tuple[contextvars.Token, t.Optional[AppContext]]] = []

    def copy(self) -> "RequestContext":
        """Creates a copy of this request context with the same request object.
        This can be used to move a request context to a different greenlet.
        Because the actual request object is the same this cannot be used to
        move a request context to a different thread unless access to the
        request object is locked.

        .. versionadded:: 0.10

        .. versionchanged:: 1.1
           The current session object is used instead of reloading the original
           data. This prevents `flask.session` pointing to an out-of-date object.
        """
        return self.__class__(
            self.app,
            environ=self.request.environ,
            request=self.request,
        )

    def match_request(self) -> None:
        """Can be overridden by a subclass to hook into the matching
        of the request.
        """
        result = self.url_adapter.match(return_rule=True)  # type: ignore
        self.request.url_rule, self.request.view_args = result  # type: ignore

    def push(self) -> None:
        # Before we push the request context we have to ensure that there
        # is an application context.
        app_ctx = _cv_app.get(None)

        if app_ctx is None or app_ctx.app is not self.app:
            app_ctx = self.app.app_context()
            app_ctx.push()
        else:
            app_ctx = None

        self._cv_tokens.append((_cv_request.set(self), app_ctx))

        if self.url_adapter is not None:
            self.match_request()

    def pop(self, exc: t.Optional[BaseException] = None) -> None:  # type: ignore
        """Pops the request context and unbinds it by doing that.  This will
        also trigger the execution of functions registered by the
        :meth:`~flask.Flask.teardown_request` decorator.

        .. versionchanged:: 0.9
           Added the `exc` argument.
        """
        clear_request = len(self._cv_tokens) == 1

        ctx = _cv_request.get()
        token, app_ctx = self._cv_tokens.pop()
        _cv_request.reset(token)

        if clear_request:
            ctx.request.environ["werkzeug.request"] = None

        if app_ctx is not None:
            app_ctx.pop(exc)

        if ctx is not self:
            raise AssertionError(
                f"Popped wrong request context. ({ctx!r} instead of {self!r})"
            )

    def __enter__(self) -> "RequestContext":
        self.push()
        return self

    def __exit__(
            self,
            exc_type: t.Optional[type],
            exc_value: t.Optional[BaseException],
            tb: t.Optional[TracebackType],
    ) -> None:
        self.pop(exc_value)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} {self.request.url!r}"
            f" [{self.request.method}] of {'sparrow'}>"
        )
