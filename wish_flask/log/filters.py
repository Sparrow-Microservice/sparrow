import logging

from wish_flask.context.request_id_context import RequestIdContext, RequestTracingIdContext, RequestClientIdContext
from wish_flask.context.session_context import SessionSignContext
from wish_flask.context.user_id_context import UserIdContext
from wish_flask.log.meta import LoggingMixin


class ProcessorArgsMaxLengthFilter(logging.Filter, LoggingMixin):
    """Slice str argument that exceeds maximum length

    This filter only work for OfflineProcessorHandler's logger. Sometimes this
    logger invokes message and args in below format:
    e.g.
        logger.info(
            "Invoking (%s, %s)(*%s, **%s)", queue_name, unique_name, args, kwargs
        )

    if any element or value length in args or kwargs is too long, they will be
    sliced according to the maximum length settings.
    """

    def __init__(self, max_arg_length):
        self.max_arg_length = max_arg_length
        self.record = None
        super(ProcessorArgsMaxLengthFilter, self).__init__()

    def filter(self, record):
        self.record = record
        new_r_args = []
        for r_arg in record.args:
            new_r_arg = self.__filter_record_arg(r_arg)
            new_r_args.append(new_r_arg)
        record.args = tuple(new_r_args)
        return True

    def __filter_record_arg(self, r_arg):
        new_r_arg = r_arg
        try:
            if self.__is_str_type(r_arg):
                new_r_arg = self.__slice_arg(r_arg)
            elif isinstance(r_arg, tuple) \
                    or isinstance(r_arg, list):
                new_args = []
                for arg in r_arg:
                    new_arg = self.__filter_record_arg(arg)
                    new_args.append(new_arg)
                new_r_arg = tuple(new_args) \
                    if isinstance(r_arg, tuple) \
                    else new_args
            elif isinstance(r_arg, dict):
                new_kwargs = {}
                for key, arg in r_arg.items():
                    new_arg = self.__filter_record_arg(arg)
                    new_kwargs[key] = new_arg
                new_r_arg = new_kwargs
        except Exception as e:
            self.__log_error(e)
        finally:
            return new_r_arg

    @classmethod
    def __is_str_type(cls, arg):
        return isinstance(arg, str)

    def __slice_arg(self, arg):
        new_arg = arg
        try:
            if self.__is_str_type(arg) \
                    and len(arg) > self.max_arg_length:
                new_arg = arg[:self.max_arg_length] + '......'
        except Exception as e:
            self.__log_error(e)
        finally:
            return new_arg

    def __log_error(self, ex):
        self.logger.error(
            "Filter %s failed during processing logger "
            "%s with record message %s: [%s]",
            self.__class__.__name__,
            self.record.name,
            self.record.msg,
            str(ex)
        )


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = RequestIdContext.get('-')
        return True


class RequestTracingIdFilter(logging.Filter):
    def filter(self, record):
        record.request_tracing_id = RequestTracingIdContext.get('-')
        return True


class SessionSignFilter(logging.Filter):
    def filter(self, record):
        record.session_sign = SessionSignContext.get('-')
        return True


class UserIdFilter(logging.Filter):
    def filter(self, record):
        record.user_id = UserIdContext.get('-')
        return True


class RequestClientFilter(logging.Filter):
    def filter(self, record):
        record.request_id = RequestClientIdContext.get('-')
        return True
