import pprint


def _type_to_name(field_cls):
    name = field_cls.__name__
    name = name.replace("Field", "")
    return name


def _describe_field(value):
    # import inside function in case that mongoengine is not installed
    from mongoengine import fields
    assert isinstance(value, fields.BaseField)

    if isinstance(value, fields.ReferenceField):
        return "->%s" % _type_to_name(value.document_type)
    if isinstance(value, fields.EmbeddedDocumentField):
        return "{%s}" % _type_to_name(value.document_type)
    if isinstance(value, fields.ListField):
        return "[%s, ...]" % _describe_field(value.field)
    return _type_to_name(type(value))


def _describe_fields(doc_cls, indent=1):
    if not hasattr(doc_cls, "_fields"):
        return ""
    result = []
    for key, value in doc_cls._fields.items():
        # embedded douments have no id_field
        if "id_field" in doc_cls._meta and key == doc_cls._meta["id_field"]:
            key = "*" + key
            pk = True
        else:
            key = " " + key
            pk = False
        content = "%s %-20s %s" % (" " * indent,
                                   key, _describe_field(value))
        if pk:
            result.insert(0, content)
        else:
            result.append(content)
    return "\n".join(result)


def d(doc_cls):
    """
    d(doc) :
        Describe a given document class.
        [...] is list,
        {...} is embedded document,
        ->(...) is reference.
    """
    print(doc_cls.__name__)
    print(_describe_fields(doc_cls))


def __pp_convert(value, raw):
    # import inside function in case that mongoengine is not installed
    from mongoengine.base import BaseDocument
    if isinstance(value, BaseDocument):
        mongo = value.to_mongo()

        # do a shallow transformation of db_field names to more friendly names
        if not raw:
            field_map = {}
            for (field_name, field) in type(value)._fields.items():
                field_map[field.db_field] = field_name

            remapped_mongo = {}
            for (field, val) in mongo.items():
                if field in field_map:
                    field = field_map[field]

                if not field.startswith("_") and isinstance(value[field], BaseDocument):
                    val = __pp_convert(value[field], raw)
                elif not field.startswith("_") and isinstance(value[field], list):
                    val = [__pp_convert(f, raw) for f in value[field]]

                remapped_mongo[field] = val

            return remapped_mongo
        else:
            return mongo
    return value


def pp(value, indent=2, raw=False):
    """
    pp(value, indent=2) :
        Pretty-prints the value; can also be used on document instances
    """
    # transform mongoengine Documents into dicts
    result = __pp_convert(value, raw)
    pprint.pprint(result, indent=indent)
