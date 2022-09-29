from datetime import datetime

from flask_mongoengine import Document
import mongoengine.fields as f

from sparrow.extensions.mongo.operation import MongoOperation
from sparrow.lib.py_enum import PyEnumMixin


class S3Index(Document, MongoOperation):
    class State(PyEnumMixin):
        NOT_UPLOADED = 0
        UPLOADED = 1
        FAILED = 2
        DELETED = 3

    state = f.IntField(db_field="s", choices=State.get_ids())
    data_info = f.DictField(db_field="di")
    url = f.StringField(db_field="u")
    error_msg = f.StringField(db_field="em")
    generate_time = f.DateTimeField(db_field="gt", required=True)

    @classmethod
    def create(cls, data_info):
        now = datetime.utcnow()
        result = cls(data_info=data_info, generate_time=now)
        result.save(force_insert=True)
        return result

    @property
    def upload_success(self):
        return self.state == self.State.UPLOADED

    @property
    def upload_failed(self):
        return self.state == self.State.FAILED

    def after_uploaded(self, url):
        self.update(state=self.State.UPLOADED, url=url)

    def after_upload_failed(self, msg):
        self.update(state=self.State.FAILED, error_msg=msg)

    def set_deleted(self):
        self.update(state=self.State.DELETED)
