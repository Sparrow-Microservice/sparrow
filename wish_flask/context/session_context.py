import hashlib

from wish_flask.context.base_context import ValueContext
from wish_flask.context.request_attacher import RequestAttacher
from wish_flask.context.utils import expend_headers, get_header_value

SESSION_SIGN_KEY = 'SESSION_SIGN'
SESSION_SIGN_HEADERS = expend_headers('Wish-Session-Sign')


# Suppose that every login of one user will generate a unique session for the following requests,
# until that the user re-login.
class SessionSignContext(ValueContext, RequestAttacher):
    stats_key = SESSION_SIGN_KEY
    auto_attach = True

    @classmethod
    def set_session(cls, session, override=False):
        if not session:
            return None
        if not override and cls.get():
            # We have already set session sign from request headers.
            return None
        session_md5 = hashlib.md5(session).hexdigest()[:8]
        cls.set(session_md5)

    @classmethod
    def attach_from_request(cls, request, **kwargs):
        session_sign = get_header_value(request.headers, SESSION_SIGN_HEADERS)
        if session_sign:
            cls.set(session_sign)
