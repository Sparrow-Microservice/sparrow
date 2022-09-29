from werkzeug.exceptions import InternalServerError

from sparrow.exceptions.handlers.base_exp_hander import BaseExceptionHandler


class UnhandledExceptionLogger(BaseExceptionHandler):
    def handle_exception(self, error):
        pass

    def log_exception(self, exc_info):
        self.log_to_console(exc_info[1], tb=exc_info[2])
        self.log_to_td(exc_info[1], tb=exc_info[2])
        self.log_to_metrics(exc_info[1])

    @classmethod
    def response_http_code(cls, rsp):
        return InternalServerError.code
