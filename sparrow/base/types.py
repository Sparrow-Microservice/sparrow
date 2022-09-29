import typing as t
import marshmallow as ma
from marshmallow_dataclass import NewType as md_newtype, _U
from werkzeug.datastructures import FileStorage
from flask_smorest.fields import Upload
from sparrow.base import fields
from bson import ObjectId


def NewType(
    name: str,
    typ: t.Type[_U],
    field: t.Optional[t.Type[ma.fields.Field]] = None,
    **kwargs
) -> t.Type[_U]:
    new_type = md_newtype(name, typ, field=field, **kwargs)
    return t.cast(t.Type[typ], new_type)


Email = NewType("Email", str, field=fields.Email)
UUID = NewType("UUID", str, field=fields.UUID)
Url = NewType("Url", str, field=fields.Url)
File = NewType("File", FileStorage, field=Upload)
ObjectId = NewType('ObjectId', ObjectId, field=fields.ObjectId)
