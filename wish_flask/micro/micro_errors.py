from wish_flask.lib.py_enum import PyEnumMixin


class MicroErrors(PyEnumMixin):
    # micro service
    MICRO_SERVICE_ERROR = 80000
    MICRO_TIMEOUT = 80001
    MICRO_UNAUTHORIZED = 80002
    MICRO_API_NOT_EXIST = 80003
    MICRO_ERROR_END = 80099
