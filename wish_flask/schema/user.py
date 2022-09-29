from wish_flask.base.dataclasses import dataclass
import typing


@dataclass
class UserSchema(object):
    user_id: str
    user_permissions: typing.List[str]
    user_roles: typing.List[str]
