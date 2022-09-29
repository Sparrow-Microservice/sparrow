import typing

from marshmallow.fields import *
from sparrow.i18n import _l

"""
class Field:
    :param default: If set, this value will be used during serialization if the input value
        is missing. If not set, the field will be excluded from the serialized output if the
        input value is missing. May be a value or a callable.
    :param missing: Default deserialization value for the field if the field is not
        found in the input data. May be a value or a callable.
    :param data_key: The name of the dict key in the external representation, i.e.
        the input of `load` and the output of `dump`.
        If `None`, the key will match the name of the field.
    :param attribute: The name of the attribute to get the value from when serializing.
        If `None`, assumes the attribute has the same name as the field.
        Note: This should only be used for very specific use cases such as
        outputting multiple fields for a single attribute. In most cases,
        you should use ``data_key`` instead.
    :param validate: Validator or collection of validators that are called
        during deserialization. Validator takes a field's input value as
        its only parameter and returns a boolean.
        If it returns `False`, an :exc:`ValidationError` is raised.
    :param required: Raise a :exc:`ValidationError` if the field value
        is not supplied during deserialization.
    :param allow_none: Set this to `True` if `None` should be considered a valid value during
        validation/deserialization. If ``missing=None`` and ``allow_none`` is unset,
        will default to ``True``. Otherwise, the default is ``False``.
    :param load_only: If `True` skip this field during serialization, otherwise
        its value will be present in the serialized data.
    :param dump_only: If `True` skip this field during deserialization, otherwise
        its value will be present in the deserialized object. In the context of an
        HTTP API, this effectively marks the field as "read-only".
    :param dict error_messages: Overrides for `Field.default_error_messages`.
    :param metadata: Extra information to be stored as field metadata.
"""


class String(String):
    default_error_messages = {
        "invalid": _l("Not a valid string."),
        "invalid_utf8": _l("Not a valid utf-8 string."),
    }

    def __init__(self, *args, **kwargs):
        self.strip = kwargs.pop('strip', True)
        super().__init__(*args, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs) -> typing.Any:
        ds_value = super()._deserialize(value, attr, data, **kwargs)
        if self.strip is True:
            return ds_value.strip()
        elif self.strip and isinstance(self.strip, str):
            return ds_value.strip(self.strip)
        return ds_value


class UUID(UUID, String):
    default_error_messages = {"invalid_uuid": _l("Not a valid UUID.")}

    def _deserialize(self, value, attr, data, **kwargs) -> typing.Any:
        ds_value = String._deserialize(self, value, attr, data, **kwargs)
        return self._validated(ds_value)


class Url(Url, String):
    default_error_messages = {"invalid": _l("Not a valid URL.")}


class Email(Email, String):
    default_error_messages = {"invalid": _l("Not a valid email address.")}


try:
    from bson import ObjectId as bObjectId
    from bson.errors import InvalidId

    class ObjectId(String):
        default_error_messages = {"invalid": _l("Not a valid ObjectID.")}

        def _deserialize(self, value, attr, data, **kwargs) -> typing.Any:
            value = super()._deserialize(value, attr, data, **kwargs)
            if value is None:
                return None
            if isinstance(value, bObjectId):
                return value
            try:
                return bObjectId(value)
            except (TypeError, ValueError, InvalidId) as error:
                raise self.make_error("invalid") from error

        def _serialize(self, value, attr, obj, **kwargs) -> typing.Optional[str]:
            if isinstance(value, bObjectId):
                value = str(value)
            return super()._serialize(value, attr, obj, **kwargs)
except:
    pass


class Decimal(Decimal):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('as_string', True)
        super().__init__(*args, **kwargs)
