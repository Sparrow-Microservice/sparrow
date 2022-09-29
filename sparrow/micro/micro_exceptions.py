from sparrow.exceptions.api_exception import StandaloneApiException
from sparrow.exceptions.errors import Errors
from sparrow.micro.exceptions import MicroApiException
from sparrow.micro.micro_errors import MicroErrors
from sparrow.i18n import _


class MicroInnerApiException(StandaloneApiException):
    def __init__(self, micro_api_exp: MicroApiException, code, msg=None):
        super(MicroInnerApiException, self).__init__(
            code=code, msg=msg or micro_api_exp.reason
        )
        self.micro_api_exp = micro_api_exp

    def __str__(self):
        s = str(self.micro_api_exp)
        s += "code: {0}\n".format(self.code)
        s += "message: {0}\n".format(self.msg)
        return s


class MicroApiErrorException(MicroInnerApiException):
    def __init__(self, micro_api_exp):
        super(MicroApiErrorException, self).__init__(
            micro_api_exp, MicroErrors.MICRO_SERVICE_ERROR, _('Micro Connection Error')
        )


class MicroApiUnauthorizedException(MicroInnerApiException):
    def __init__(self, micro_api_exp):
        super(MicroApiUnauthorizedException, self).__init__(
            micro_api_exp, MicroErrors.MICRO_UNAUTHORIZED, _('Micro Authentication Error')
        )


class MicroApiValidationException(MicroInnerApiException):
    def __init__(self, micro_api_exp):
        super(MicroApiValidationException, self).__init__(
            micro_api_exp, Errors.VALIDATE_FAILED, _('Api Validation Error')
        )
