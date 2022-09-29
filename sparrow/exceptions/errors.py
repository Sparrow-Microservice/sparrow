from sparrow.lib.py_enum import PyEnumMixin


class Errors(PyEnumMixin):
    SUCCESS = 0
    FORBIDDEN = 403
    NOT_FOUND = 404
    VALIDATE_FAILED = 422

    UNKNOWN = 500
