from werkzeug.http import dump_cookie


class Cookie(object):

    COOKIE_KEY = "Set-Cookie"

    def __init__(
            self,
            key,
            **kwargs
    ):
        """Generate cookie

        :param key: the key (name) of the cookie to be set.
        :param value: the value of the cookie.
        :param max_age: should be a number of seconds, or `None` (default) if
                        the cookie should last only as long as the client's
                        browser session.
        :param expires: should be a `datetime` object or UNIX timestamp.
        :param path: limits the cookie to a given path, per default it will
                     span the whole domain.
        :param domain: if you want to set a cross-domain cookie.  For example,
                       ``domain=".example.com"`` will set a cookie that is
                       readable by the domain ``www.example.com``,
                       ``foo.example.com`` etc.  Otherwise, a cookie will only
                       be readable by the domain that set it.
        :param secure: If `True`, the cookie will only be available via HTTPS
        :param httponly: disallow JavaScript to access the cookie.  This is an
                         extension to the cookie standard and probably not
                         supported by all browsers.
        :param samesite: Limits the scope of the cookie such that it will only
                         be attached to requests if those requests are
                         "same-site".
        :param charset:
        :param max_cookie_size:
        """
        self.key = key
        self.kwargs = kwargs

    def make_header(self):
        return {
            Cookie.COOKIE_KEY: dump_cookie(
                self.key,
                **self.kwargs
            )
        }

    @classmethod
    def make_header_multi(cls, *cookies):
        header = {Cookie.COOKIE_KEY: []}
        if len(cookies) == 1 and isinstance(cookies[0], (list, tuple)):
            cookies = cookies[0]
        for c in cookies:
            header[Cookie.COOKIE_KEY].append(c.make_header()[Cookie.COOKIE_KEY])
        return header
