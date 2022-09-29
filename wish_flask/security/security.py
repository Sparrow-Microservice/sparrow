"""
Contains classes for security types.
"""
import urllib3
from flask import request


class SecurityScheme(object):
    """Represents security scheme"""

    def __init__(self, schema_name, scopes):
        self.schema_name = schema_name
        self.scopes = scopes or []

    def spec(self):
        return {}

    def check(self):
        return False


class APIKey(SecurityScheme):
    def __init__(self, schema_name, name, location="header", scopes=None):
        self.name = name
        self.location = location if location in ("query", "header", "cookie") else "header"
        super(APIKey, self).__init__(schema_name, scopes)

    @property
    def type(self):
        return "apiKey"

    def spec(self):
        return {
            "type": self.type,
            "name": self.name,
            "in": self.location
        }


class HTTP(SecurityScheme):
    # from http://www.iana.org/assignments/http-authschemes/http-authschemes.xhtml
    Schemes = ['basic', 'bearer', 'digest', 'hoba', 'mutual', 'negotiate', 'oauth', 'scram-sha-1',
               'scram-sha-256', 'vapid']

    def __init__(self, schema_name, scheme, bearer_format=None, scopes=None):
        self.scheme = scheme
        self.bearer_format = bearer_format
        super(HTTP, self).__init__(schema_name, scopes)

    @property
    def type(self):
        return "http"

    def spec(self):
        sp = {
            "type": self.type,
            "scheme": self.scheme,
        }
        if self.bearer_format:
            sp["bearerFormat"] = self.bearer_format
        return sp


class BasicHTTP(HTTP):
    def __init__(self, schema_name, bearer_format=None, scopes=None, auth_value=None):
        super().__init__(schema_name, 'basic', bearer_format=bearer_format, scopes=scopes)
        self.auth_header = None
        if auth_value and ':' in auth_value:
            self.auth_header = urllib3.util.make_headers(basic_auth=auth_value).get('authorization')

    def check(self):
        if request:
            if not self.auth_header:
                return False
            auth = request.headers.get('Authorization')
            return auth and auth == self.auth_header
        return True
