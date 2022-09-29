from bson import ObjectId, SON, DBRef
from datetime import date
from datetime import datetime
from mongoengine.errors import InvalidQueryError, ValidationError
from pymongo.read_preferences import ReadPreference
from mongoengine.base.fields import BaseField
from mongoengine.connection import _get_db
import contextlib
import threading
import pymongo
from mongoengine.queryset import OperationError
import warnings
from wish_flask.extensions.mongo.mongo_comment import MongoComment
from mongoengine import Document

__all__ = ("MongoOperation", "NO_TIMEOUT_DEFAULT", "read_preference_dict")

NO_TIMEOUT_DEFAULT = object()

BY_IDS_LIMIT = 10000
THREAD_LOCAL = threading.local()
read_preference_dict = {
    "offline": ReadPreference.SECONDARY_PREFERRED,
    False: ReadPreference.PRIMARY,
    True: ReadPreference.SECONDARY_PREFERRED,
}


class ArbitraryField(BaseField):
    def validate(self, value):
        return True

    def to_python(self, value):
        return value


class WrappedCounter(object):

    def __init__(self):
        self.value = 0

    def inc(self):
        self.value += 1

    def get(self):
        return self.value


class BulkOperationError(OperationError):
    pass


class FieldNotLoadedError(Exception):
    def __init__(self, collection_name, field_name):
        self.collection_name = collection_name
        self.field_name = field_name
        super(FieldNotLoadedError, self).__init__(
            'Field accessed, but not loaded: %s.%s' % (collection_name,
                                                       field_name))


def _transform_hint(cls, hint_doc):
    new_hit_doc = []
    for i, index_field in enumerate(hint_doc):
        field, direction = hint_doc[i]
        db_field, context = _transform_key(field, cls)
        new_hit_doc.append((db_field, direction))

    return new_hit_doc


def _transform_fields(cls, fields=None, excluded_fields=None):
    if fields is not None and excluded_fields is not None:
        raise ValueError(
            'Cannot specify both included and excluded fields.'
        )

    if isinstance(fields, dict):
        new_fields = {}
        for key, val in fields.items():
            db_key, field = _transform_key(key, cls, is_find=True)
            if isinstance(val, dict):
                if list(val.keys()) not in (['$elemMatch'], ['$slice']):
                    raise ValueError('Invalid field value')
                new_fields[key] = _transform_value(val, field, fields=True)
            else:
                if val not in [0, 1]:
                    raise ValueError('Invalid field value')
                new_fields[key] = val
        fields = new_fields
    elif isinstance(fields, (list, tuple)):
        res = {}
        for f in fields:
            if f == "_id":
                f = "id"
            res[f] = 1
        fields = res
        # fields = {
        #     f: 1 for f in fields
        # }
        # fields = {
        #     _transform_key(f, cls, is_find=True)[0]: 1 for f in fields
        # }
    elif isinstance(excluded_fields, (list, tuple)):
        fields = {
            f: 0 for f in excluded_fields
        }
        # fields = {
        #     _transform_key(f, cls, is_find=True)[0]: 0 for f in excluded_fields
        # }
        pass
    return fields


def _transform_id_reference_value(value, context, op_type):
    """
        Transform strings/documents into ObjectIds / DBRefs when appropriate

        This is slightly tricky because there are List(ReferenceField) and
        List(ObjectIdField) and you sometimes get lists of documents/strings
        that need conversion.

        op_type is 'value' (if it's an individual value), 'list_all' (if it's a
        list of values), 'list' (if it's going into a list but is an individual
        value), or None (if it's neither).

        If no conversion is necessary, just return the original value
    """

    from mongoengine.fields import ReferenceField, ObjectIdField, ListField

    # not an op we can work with
    if not op_type:
        return value

    if isinstance(context, ListField):
        f = context.field
    else:
        f = context

    if not isinstance(f, ObjectIdField) and \
            not isinstance(f, ReferenceField):
        return value

    # the logic is a bit complicated here. there are a few different
    # variables at work. the op can be value, list, or list_all and it can
    # be done on a list or on a single value. the actions are either we do
    # single conversion or we need to convert each element in a list.
    #
    # see _transform_value for the logic on what's a value, list, or
    # list_all.
    #
    # here's the matrix:
    #
    # op         type     outcome
    # --------   ------   -----------
    # value      list     convert all
    # list       list     convert one
    # list_all   list     convert all
    # value      single   convert one
    # list       single   invalid
    # list_all   single   convert all

    if not isinstance(context, ListField) and op_type == 'list':
        raise ValidationError("Can't do list operations on non-lists")

    if op_type == 'list_all' or \
            (isinstance(context, ListField) and op_type == 'value'):
        if not isinstance(value, list) and not isinstance(value, tuple):
            raise ValidationError("Expecting list, not value")

        if isinstance(f, ReferenceField):
            new_value = []

            for v in value:
                if isinstance(v, DBRef):
                    new_value.append(v)
                elif isinstance(v, Document):
                    new_value.append(DBRef(type(v)._meta['collection'], v.id))
                else:
                    raise ValidationError("Invalid ReferenceField value")

            return new_value
        else:
            return [ObjectId(v) for v in value]
    else:
        if isinstance(value, list) or isinstance(value, tuple):
            raise ValidationError("Expecting value, not list")

        if isinstance(f, ReferenceField):
            if isinstance(value, DBRef):
                return value
            return DBRef(type(value)._meta['collection'], value.id)
        else:
            if value is None and not f.primary_key:
                return value
            return ObjectId(value)

    raise AssertionError("Failed to convert")


def _transform_key(key, context, prefix='', is_find=False):
    from mongoengine.fields import BaseField, DictField, ListField, \
        EmbeddedDocumentField
    from mongoengine.base import get_document, BaseDocument

    parts = key.split('.', 1)
    first_part = parts[0]

    if len(parts) > 1:
        rest = parts[1]
    else:
        rest = None

    # a key as a digit means a list index... set context as the list's value
    if first_part.isdigit() or first_part == '$':
        if isinstance(context, DictField):
            context = ArbitraryField()
        elif isinstance(context.field, str):
            context = get_document(context.field)
        elif isinstance(context.field, BaseField):
            context = context.field

    if first_part == '_id':
        context = context._fields[context._meta['id_field']]

    # atomic ops, digits (list indexes), or _ids get no processing
    if first_part[0] == '$' or first_part.isdigit() or first_part == '_id':
        if prefix:
            new_prefix = "%s.%s" % (prefix, first_part)
        else:
            new_prefix = first_part

        if rest:
            return _transform_key(rest, context, prefix=new_prefix,
                                  is_find=is_find)
        else:
            return new_prefix, context

    def is_subclass_or_instance(obj, parent):
        try:
            if issubclass(obj, parent):
                return True
        except TypeError:
            if isinstance(obj, parent):
                return True

        return False

    field = None

    if is_subclass_or_instance(context, BaseDocument):
        field = context._fields.get(first_part, None)
    elif is_subclass_or_instance(context, EmbeddedDocumentField):
        field = context.document_type._fields.get(first_part, None)
    elif is_subclass_or_instance(context, ListField):
        if is_subclass_or_instance(context.field, str):
            field = get_document(context.field)
        elif is_subclass_or_instance(context.field, BaseField):
            field = context.field
        else:
            raise ValueError("Can't parse field %s" % first_part)
        setattr(field, "_in_list", True)

    # if we hit a DictField, values can be anything, so use the sentinal
    # ArbitraryField value (I prefer this over None, since None can be
    # introduced in other ways that would be considered errors & should not
    # be silently ignored)
    elif is_subclass_or_instance(context, DictField):
        field = ArbitraryField()
    elif is_subclass_or_instance(context, ArbitraryField):
        field = context

    if not field:
        raise ValueError("Can't find field %s" % first_part)

    # another unfortunate hack... in find queries "list.field_name" means
    # field_name inside of the list's field... but in updates,
    # list.0.field_name means that... need to differentiate here
    list_field_name = None
    if is_subclass_or_instance(field, ListField) and is_find:
        list_field_name = field.db_field
        if is_subclass_or_instance(field.field, str):
            field = get_document(field.field)
        elif is_subclass_or_instance(field.field, BaseField):
            field = field.field
        else:
            raise ValueError("Can't parse field %s" % first_part)
        setattr(field, "_in_list", True)

    if is_subclass_or_instance(field, ArbitraryField):
        db_field = first_part
    elif list_field_name:
        db_field = list_field_name
    else:
        db_field = field.db_field

    if prefix:
        if db_field is not None:
            result = "%s.%s" % (prefix, db_field)
        else:
            result = prefix
            rest = key

    else:
        result = db_field

    if rest:
        return _transform_key(rest, field, prefix=result, is_find=is_find)
    else:
        return result, field


def _transform_value(value, context, op=None, validate=True, fields=False):
    from mongoengine.fields import DictField, EmbeddedDocumentField, ListField
    from mongoengine.base import BaseDocument

    VALIDATE_OPS = ['$set', '$inc', None, '$eq', '$gte', '$lte', '$lt',
                    '$gt', '$ne', '$setOnInsert']
    SINGLE_LIST_OPS = [None, '$gt', '$lt', '$gte', '$lte', '$ne']
    LIST_VALIDATE_OPS = ['$addToSet', '$push', '$pull']
    LIST_VALIDATE_ALL_OPS = ['$pushAll', '$pullAll', '$each', '$in',
                             '$nin', '$all']
    NO_VALIDATE_OPS = ['$unset', '$pop', '$rename', '$bit',
                       '$all', '$and', '$or', '$exists', '$mod',
                       '$elemMatch', '$size', '$type', '$not', '$returnKey',
                       '$maxScan', '$orderby', '$explain', '$snapshot',
                       '$max', '$min', '$showDiskLoc', '$hint', '$comment',
                       '$slice']

    # recurse on list, unless we're at a ListField
    if isinstance(value, list) and not isinstance(context, ListField):
        transformed_list = []
        for listel in value:
            if isinstance(listel, dict) and not isinstance(context, DictField):
                transformed_value = SON()

                for key, subvalue in listel.items():
                    if key[0] == '$':
                        op = key

                    new_key, value_context = _transform_key(key, context,
                                                            is_find=(
                                                                    op is None))

                    transformed_value[new_key] = \
                        _transform_value(subvalue, value_context,
                                         op, validate, fields)

                    transformed_list.append(transformed_value)
            else:
                transformed_list.append(listel)
        value = transformed_list

    # recurse on dict, unless we're at a DictField
    if isinstance(value, dict) and not isinstance(context, DictField):
        transformed_value = SON()

        for key, subvalue in value.items():
            if key[0] == '$':
                op = key

            new_key, value_context = _transform_key(key, context,
                                                    is_find=(op is None))

            transformed_value[new_key] = \
                _transform_value(subvalue, value_context,
                                 op, validate, fields)

        return transformed_value
    # if we're in a dict field and there's operations on it, recurse
    elif isinstance(value, dict) and value and list(value.keys())[0][0] == '$':
        transformed_value = SON()

        for key, subvalue in value.items():
            op = key

            new_key, value_context = _transform_key(key, context,
                                                    is_find=(op is None))
            transformed_value[new_key] = \
                _transform_value(subvalue, value_context,
                                 op, validate, fields)

        return transformed_value
    # else, validate & return
    else:
        op_type = None
        # there's a special case here, since some ops on lists
        # behaves like a LIST_VALIDATE_OP (i.e. it has "x in list" instead
        # of "x = list" semantics or x not in list, etc).
        if op in LIST_VALIDATE_ALL_OPS or \
                (op is None and
                 getattr(context, "_in_list", None) and
                 (isinstance(value, list) or
                  isinstance(value, tuple))):
            op_type = 'list_all'
        elif op in LIST_VALIDATE_OPS or \
                (op in SINGLE_LIST_OPS and isinstance(context, ListField)):
            op_type = 'list'
        elif op in VALIDATE_OPS:
            op_type = 'value'

        value = _transform_id_reference_value(value, context,
                                              op_type)

        if validate and not isinstance(context, ArbitraryField):
            # the caveat to the above is that those semantics are modified if
            # the value is a list. technically this isn't completely correct
            # since passing a list has a semantic of field == value OR value
            # IN field (the underlying implementation is probably that all
            # queries have (== or IN) semantics, but it's only relevant for
            # lists). so, this code won't work in a list of lists case where
            # you want to match lists on value
            if op in LIST_VALIDATE_ALL_OPS or \
                    (op is None and
                     getattr(context, "_in_list", None) and
                     (isinstance(value, list) or
                      isinstance(value, tuple))):
                for entry in value:
                    if isinstance(context, ListField):
                        context.field.validate(entry)
                    else:
                        context.validate(entry)
            # same special case as above (for {list: x} meaning "x in list")
            elif op in LIST_VALIDATE_OPS or \
                    (op in SINGLE_LIST_OPS and isinstance(context, ListField)):
                context.field.validate(value)
            elif op in VALIDATE_OPS:
                context.validate(value)
            elif op not in NO_VALIDATE_OPS:
                raise ValidationError("Unknown atomic operator %s" % op)

        # handle $slice by enforcing negative int
        if op == '$slice':
            if fields:
                if not ((isinstance(value, list) or
                         isinstance(value, tuple)) and len(value) == 2) \
                        and not isinstance(value, int):
                    raise ValidationError("Projection slices must be "
                                          "2-lists or ints")
            elif not isinstance(value, int) or value > 0:
                raise ValidationError("Slices must be negative ints")

        # handle EmbeddedDocuments
        elif isinstance(value, BaseDocument):
            value = value.to_mongo()

        # handle EmbeddedDocuments in lists
        elif isinstance(value, list):
            value = [v.to_mongo() if isinstance(v, BaseDocument) else v
                     for v in value]

        # handle lists (force to_mongo() everything if it's a list of docs)
        elif isinstance(context, ListField) and \
                isinstance(context.field, EmbeddedDocumentField):
            value = [d.to_mongo() for d in value]

        # handle dicts (just blindly to_mongo() anything that'll take it)
        elif isinstance(context, DictField):
            for k, v in value.items():
                if isinstance(v, BaseDocument):
                    value[k] = v.to_mongo()

        return value


class MongoOperation(object):
    # meta = {
    #     "hash_field": None
    # }

    def to_dict_default(self, date_format="%Y-%m-%d", ignore_unloaded=False):
        """
        Default to_dict, can be overridden
        Returns all fields, with values transformed:
            - ObjectIds casted to strings
            - Date/Datetime formatted as string, with format specified by
                default_date_format property of class
            - Values of lists and dicts recursively transformed
        """
        def transform_field(v):
            if isinstance(v, ObjectId):
                v = str(v)
            elif isinstance(v, list):
                v = list(map(transform_field, v))
            elif issubclass(v.__class__, MongoOperation):
                if hasattr(v, "to_dict"):
                    v = v.to_dict()
                else:
                    v = v.to_dict_default(ignore_unloaded=ignore_unloaded)
            elif isinstance(v, dict):
                v = dict(
                    [(key, transform_field(val)) for key, val in v.items()]
                )
            elif isinstance(v, (datetime, date)):
                if date_format is not None:
                    v = v.strftime(date_format)
            return v

        _dict = {}
        for fname in self._fields.keys():
            try:
                value = getattr(self, fname)
            except FieldNotLoadedError:
                # In case fields was specified, some fields may not be
                # loaded, so just skip from unloaded fields
                if not ignore_unloaded:
                    raise
            else:
                _dict[fname] = transform_field(value)
        return _dict

    @classmethod
    def by_id(cls, id):
        return cls.objects(pk=id).first()

    @classmethod
    def _trans_query(cls, spec, fields=None, skip=0, limit=0, sort=None,
                     slave_ok=True, excluded_fields=None, max_time_ms=None,
                     timeout_value=NO_TIMEOUT_DEFAULT, session=None, **kwargs):
        """

        :param spec:
        :param fields: dict, list, tuple. Only the fields to load.
        :param excluded_fields: dict, list, tuple. Exclude the fields to load.
        :param skip: int. The docs to skip.
        :param limit: int.
        :param sort: list of tuple. e.g. [("datetime", 1)], 1 for ascending and -1 for descending.
        :param slave_ok: bool. True for SECONDARY_PREFERRED. False for PRIMARY db.
        :param max_time_ms: Specifies a time limit for a query operation. If the specified time
            is exceeded, the operation will be aborted and :exc:`~pymongo.errors.ExecutionTimeout` is raised.
        """
        query = _transform_value(spec, cls)
        objects = cls.objects(__raw__=query)
        fields = _transform_fields(cls, fields, excluded_fields)
        if fields is not None:
            objects = objects.fields(**fields)
        if limit:
            objects = objects.limit(limit)
        if skip:
            objects = objects.skip(skip)
        if sort:
            if not isinstance(sort, list) or not all(
                    isinstance(k, tuple) for k in sort):
                raise ValueError('Wrong type in sort')
            args = [f"""{"+" if k[1] == 1 else "-"}{k[0].replace(".", "__")}"""
                    for k in sort]
            objects = objects.order_by(*args)

        read_preference = read_preference_dict.get(slave_ok)
        if read_preference:
            objects = objects.read_preference(read_preference)
        if max_time_ms:
            objects = objects._chainable_method("max_time_ms", max_time_ms)
        # TODO: figure out timeout_value
        # if timeout_value:
        #     objects = objects.timeout()
        return objects

    @classmethod
    def find_one(cls, spec, fields=None, skip=0, sort=None, slave_ok=True,
                 excluded_fields=None, max_time_ms=None,
                 timeout_value=NO_TIMEOUT_DEFAULT, session=None, **kwargs):
        objects = cls._trans_query(
            spec,
            fields=fields,
            skip=skip,
            sort=sort,
            slave_ok=slave_ok,
            excluded_fields=excluded_fields,
            max_time_ms=max_time_ms,
            timeout_value=timeout_value,
            session=session,
            **kwargs
        )
        return objects.first()

    @classmethod
    def find(cls, spec, fields=None, skip=0, limit=0, sort=None,
             slave_ok=True, excluded_fields=None, max_time_ms=None,
             timeout_value=NO_TIMEOUT_DEFAULT, session=None, **kwargs):
        objects = cls._trans_query(
            spec,
            fields=fields,
            skip=skip,
            limit=limit,
            sort=sort,
            slave_ok=slave_ok,
            excluded_fields=excluded_fields,
            max_time_ms=max_time_ms,
            timeout_value=timeout_value,
            session=session,
            **kwargs
        )
        return [o for o in objects]

    @classmethod
    def find_iter(cls, spec, fields=None, skip=0, limit=0, sort=None,
                  slave_ok=True, excluded_fields=None, max_time_ms=None,
                  timeout_value=NO_TIMEOUT_DEFAULT, session=None, **kwargs):
        objects = cls._trans_query(
            spec,
            fields=fields,
            skip=skip,
            limit=limit,
            sort=sort,
            slave_ok=slave_ok,
            excluded_fields=excluded_fields,
            max_time_ms=max_time_ms,
            timeout_value=timeout_value,
            session=session,
            **kwargs
        )
        return objects

    @classmethod
    def update_doc(cls, spec, document, upsert=False, multi=True,
                   session=None, **kwargs):
        objects = cls._trans_query(spec, **kwargs)
        query = _transform_value(document, cls, op="$set")
        return objects.update(upsert=upsert, multi=multi, __raw__=query)

    def update_one(self, document, upsert=False):
        # adam.update_one({"$push": {"number_list": {"$each": [50, 51, 52], "$slice": -20}}})
        if not document:
            raise ValueError("Cannot do empty updates")
        id = self.id
        res = self.update_doc({'_id': str(id)}, document, upsert=False,
                              multi=False)
        self.reload()
        return res

    @classmethod
    def remove(cls, spec, session=None, **kwargs):
        return cls._trans_query(spec, **kwargs).delete()

    @classmethod
    def count(cls, spec, slave_ok=True, max_time_ms=None,
              timeout_value=NO_TIMEOUT_DEFAULT,
              session=None, **kwargs):
        objects = cls._trans_query(
            spec,
            slave_ok=slave_ok,
            max_time_ms=max_time_ms,
            timeout_value=timeout_value,
            session=session,
            **kwargs
        )
        return objects.count()

    @classmethod
    def by_ids(cls, ids, fields=None, slave_ok=True, timeout_value=NO_TIMEOUT_DEFAULT,
               max_time_ms=None, **kwargs):
        """
            Returns a list of documents with the given ids.
            :param ids:
            :param fields:

        """
        if len(ids) > BY_IDS_LIMIT:
            raise RuntimeError("Exceeded limit of ids to query")

        if not ids:
            return []

        # grab the ID from DBRefs
        if isinstance(ids[0], DBRef):
            ids = [id.id for id in ids]

        query = {"_id": {"$in": ids}}

        objects = cls.find(
            query,
            fields=fields,
            slave_ok=slave_ok,
            timeout_value=timeout_value,
            max_time_ms=max_time_ms,
            **kwargs
        )
        return objects

    @classmethod
    def by_ids_dict(
            cls,
            ids,
            fields=None,
            slave_ok=None,
            timeout_value=NO_TIMEOUT_DEFAULT,
            max_time_ms=None,
            **kwargs
    ):
        docs = cls.by_ids(
            ids,
            fields=fields,
            slave_ok=slave_ok,
            timeout_value=timeout_value,
            max_time_ms=max_time_ms,
            **kwargs
        )
        return dict([(d.id, d) for d in docs])

    @classmethod
    def _update_spec(cls, spec, cursor_comment=True, comment=None, **kwargs):
        if cls._meta.get('allow_inheritance'):
            spec['_types'] = cls._class_name

    @classmethod
    def pk_field(cls):
        return cls._fields[cls._meta['id_field']]

    @classmethod
    def _pymongo(cls, read_preference=None):
        if not hasattr(cls, '_pymongo_collection'):
            cls._pymongo_collection = \
                _get_db(cls._meta.get('db_alias', 'default'))[
                    cls._meta['collection']]
        if read_preference:
            return cls._pymongo_collection.with_options(
                read_preference=read_preference)
        return cls._pymongo_collection

    BULK_INDEX = "bulk_index"
    BULK_SAVE_OBJECTS = "bulk_save_objects"
    BULK_OP = "bulk_op"

    @classmethod
    def _bulk_name(cls, name):
        return "_bulk_%s_%s" % (name, cls.__name__)

    @classmethod
    def _get_bulk_attr(cls, name):
        name = cls._bulk_name(name)
        if hasattr(THREAD_LOCAL, name):
            return getattr(THREAD_LOCAL, name)
        return None

    @classmethod
    def _init_bulk_attr(cls, name, default):
        name = cls._bulk_name(name)
        if not hasattr(THREAD_LOCAL, name) or getattr(THREAD_LOCAL,
                                                      name) is None:
            setattr(THREAD_LOCAL, name, default)
        return getattr(THREAD_LOCAL, name, default)

    @classmethod
    def _clear_bulk_attr(cls, name):
        setattr(THREAD_LOCAL, cls._bulk_name(name), None)

    @classmethod
    def _update_spec(cls, spec, cursor_comment=True, comment=None, **kwargs):
        if cls._meta.get('allow_inheritance'):
            spec['_types'] = cls._class_name
        if cursor_comment is True and spec:
            if not comment:
                comment = MongoComment.get_query_comment()
            spec['$comment'] = comment
        return spec

    @classmethod
    def _hash(cls, value):
        if value is None:
            raise ValueError("Shard hash key is None")
        return hash(str(value))

    @classmethod
    @contextlib.contextmanager
    def bulk(cls, allow_empty=None, unordered=False, session=None):
        if cls._get_bulk_attr(cls.BULK_OP) is not None:
            raise RuntimeError('Cannot nest bulk operations')
        try:
            cls._init_bulk_attr(cls.BULK_INDEX, WrappedCounter())
            cls._init_bulk_attr(cls.BULK_SAVE_OBJECTS, dict())
            cls._init_bulk_attr(cls.BULK_OP, list())
            yield
            try:
                bulk_ops = cls._get_bulk_attr(cls.BULK_OP)
                cls._pymongo().bulk_write(bulk_ops, ordered=not unordered,
                                          session=session)

                for object_id, props in cls._get_bulk_attr(
                        cls.BULK_SAVE_OBJECTS).items():
                    instance = props['obj']
                    if instance.id is None:
                        id_field = cls.pk_field()
                        id_name = id_field.name or 'id'
                        instance[id_name] = id_field.to_python(object_id)
            except pymongo.errors.BulkWriteError as e:
                wc_errors = e.details.get('writeConcernErrors')
                w_error = e.details['writeErrors'][0] if e.details.get(
                    'writeErrors') else None

                if wc_errors:
                    messages = '\n'.join(_['errmsg'] for _ in wc_errors)
                    message = 'Write concern errors for bulk op: %s' % messages
                elif w_error:
                    for object_id, props in cls._get_bulk_attr(
                            cls.BULK_SAVE_OBJECTS).items():
                        if props['index'] < w_error['index']:
                            instance = props['obj']
                            if instance.id is None:
                                id_field = cls.pk_field()
                                id_name = id_field.name or 'id'
                                instance[id_name] = id_field.to_python(
                                    object_id)

                    message = 'Write errors for bulk op: %s' % w_error['errmsg']

                bo_error = BulkOperationError(message)
                bo_error.details = e.details
                if w_error:
                    bo_error.op = w_error['op']
                    bo_error.index = w_error['index']
                raise bo_error
            except pymongo.errors.InvalidOperation as e:
                if 'No operations' in str(e):
                    if allow_empty is None:
                        warnings.warn('Empty bulk operation; use allow_empty')
                    elif allow_empty is False:
                        raise
                    else:
                        pass
                else:
                    raise
            except pymongo.errors.OperationFailure as err:
                message = u'Could not perform bulk operation (%s)' % err.message
                raise OperationError(message)
        finally:
            cls._clear_bulk_attr(cls.BULK_OP)
            cls._clear_bulk_attr(cls.BULK_INDEX)
            cls._clear_bulk_attr(cls.BULK_SAVE_OBJECTS)

    @classmethod
    def bulk_update(cls, spec, document, upsert=False, multi=True, **kwargs):
        if cls._get_bulk_attr(cls.BULK_OP) is None:
            raise RuntimeError(
                'Cannot do bulk operation outside of bulk context')

        document = _transform_value(document, cls, op='$set')
        spec = _transform_value(spec, cls)

        if not document:
            raise ValueError("Cannot do empty updates")

        if not spec:
            raise ValueError("Cannot do empty specs")

        spec = cls._update_spec(spec, **kwargs)
        bulk_step = {
            'filter': spec,
            'document': document
        }

        bulk_op = cls._get_bulk_attr(cls.BULK_OP)
        if upsert:
            bulk_step['op'] = 'upsert'
        else:
            if multi:
                bulk_step['op'] = 'update_all'
            else:
                bulk_step['op'] = 'update'

        if multi:
            op = pymongo.operations.UpdateMany(spec, document, upsert)
        else:
            op = pymongo.operations.UpdateOne(spec, document, upsert)
        bulk_op.append(op)
        cls._get_bulk_attr(cls.BULK_INDEX).inc()

    @classmethod
    def bulk_remove(cls, spec, multi=True, **kwargs):
        if cls._get_bulk_attr(cls.BULK_OP) is None:
            raise RuntimeError(
                'Cannot do bulk operation outside of bulk context')

        spec = _transform_value(spec, cls)

        if not spec:
            raise ValueError("Cannot do empty specs")

        spec = cls._update_spec(spec, **kwargs)
        bulk_op = cls._get_bulk_attr(cls.BULK_OP)

        if multi:
            op = pymongo.operations.DeleteMany(spec)
        else:
            op = pymongo.operations.DeleteOne(spec)
        bulk_op.append(op)
        cls._get_bulk_attr(cls.BULK_INDEX).inc()

    def bulk_save(self, validate=True):
        cls = self.__class__
        if cls._get_bulk_attr(cls.BULK_OP) is None:
            raise RuntimeError(
                'Cannot do bulk operation outside of bulk context')
        id_field = cls.pk_field()
        id_name = id_field.name or 'id'
        doc = self.to_mongo()
        if self[id_name] is None:
            object_id = ObjectId()
            doc[id_field.db_field] = id_field.to_mongo(object_id)
            self[id_name] = object_id
        else:
            object_id = self[id_name]

        # if cls._meta['hash_field']:
        #     if cls._meta['hash_field'] == cls._meta['id_field']:
        #         hash_value = object_id
        #     else:
        #         hash_value = self[cls._meta['hash_field']]
        #
        #     self['shard_hash'] = cls._hash(hash_value)
        #     hash_field = cls._fields[cls._meta['hash_field']]
        #     doc[hash_field.db_field] = hash_field.to_mongo(self['shard_hash'])
        if validate:
            self.validate()
        bulk_op = cls._get_bulk_attr(cls.BULK_OP)

        op = pymongo.operations.InsertOne(doc)
        bulk_op.append(op)
        cls._get_bulk_attr(cls.BULK_SAVE_OBJECTS)[object_id] = {
            'index': cls._get_bulk_attr(cls.BULK_INDEX).get(),
            'obj': self
        }
        cls._get_bulk_attr(cls.BULK_INDEX).inc()
        return object_id

    def set(self, **kwargs):
        return self.update_one({'$set': kwargs})

    def unset(self, **kwargs):
        return self.update_one({'$unset': kwargs})

    def inc(self, **kwargs):
        return self.update_one({'$inc': kwargs})

    def push(self, **kwargs):
        return self.update_one({'$push': kwargs})

    def pull(self, **kwargs):
        return self.update_one({'$pull': kwargs})

    def add_to_set(self, **kwargs):
        return self.update_one({'$addToSet': kwargs})
