from dataclasses import *
from dataclasses import dataclass as dc_dataclass
from dataclasses import field as dc_field
from marshmallow_dataclass import MEMBERS_WHITELIST
from wish_flask.constent import SCHEMA_NAME_EXT


def field(*, default=MISSING, default_factory=MISSING, init=True, repr=True,
          hash=None, compare=True, metadata=None, **kwargs):
    if kwargs:
        metadata = metadata or {}
        metadata.update(kwargs)
    return dc_field(
        default=default, default_factory=default_factory, init=init, repr=repr,
        hash=hash, compare=compare, metadata=metadata
    )


MEMBERS_WHITELIST.add(SCHEMA_NAME_EXT)


def dataclass(_cls=None, *, init=True, repr=True, eq=True, order=False,
              unsafe_hash=False, frozen=False, schema_name_ext=None):
    dc_rt = dc_dataclass(
        _cls, init=init, repr=repr, eq=eq, order=order,
        unsafe_hash=unsafe_hash, frozen=frozen
    )
    if _cls:
        if schema_name_ext:
            setattr(dc_rt, SCHEMA_NAME_EXT, schema_name_ext)
        return dc_rt

    def wrap(cls):
        dc = dc_rt(cls)
        if schema_name_ext:
            setattr(dc, SCHEMA_NAME_EXT, schema_name_ext)
        return dc
    return wrap
