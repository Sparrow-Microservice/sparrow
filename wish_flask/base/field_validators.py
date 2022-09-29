import typing

from marshmallow.validate import Validator
from marshmallow.validate import URL
from marshmallow.validate import Email
from marshmallow.validate import Range
from marshmallow.validate import Length
from marshmallow.validate import Equal
from marshmallow.validate import Regexp
from marshmallow.validate import Predicate
from marshmallow.validate import NoneOf
from marshmallow.validate import OneOf
from marshmallow.validate import ContainsOnly
from marshmallow.validate import ContainsNoneOf

from wish_flask.i18n import _l


class URL(URL):
    default_message = _l("Not a valid URL.")


class Email(Email):
    default_message = _l("Not a valid email address.")


class Length(Length):
    message_min = _l("Shorter than minimum length {min}.")
    message_max = _l("Longer than maximum length {max}.")
    message_all = _l("Length must be between {min} and {max}.")
    message_equal = _l("Length must be {equal}.")


class NotEmpty(Length):
    def __init__(self):
        super().__init__(min=1)


# Used for string
class NotBlank(NotEmpty):
    def __call__(self, value) -> typing.Any:
        if isinstance(value, (str, bytes)):
            value = value.strip()
        return super().__call__(value)

# TODO Translate for other validators
