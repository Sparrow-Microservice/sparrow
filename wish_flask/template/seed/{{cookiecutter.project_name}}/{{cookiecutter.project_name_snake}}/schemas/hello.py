from wish_flask.base.dataclasses import dataclass


@dataclass
class NameQuerySchema(object):
    name: str


@dataclass
class HelloMsgSchema(object):
    message: str
