from sparrow.lib.py_enum import PyEnumMixin
from sparrow.lib.s3.models import S3Index
from sparrow.log.meta import LoggingMixin

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sparrow.lib.s3.abstract_s3 import BaseS3Abstraction


class ActionType(PyEnumMixin):
    INIT = 0
    RUN = 1
    COMPLETE = 2


class S3Utils(LoggingMixin):
    # At least size of 5MB for each part, we use 6MB
    MULTI_PART_SIZE_LIMIT_BYTES = 6 * 1024 * 1024

    def __init__(
            self,
            s3_instance: 'BaseS3Abstraction',
            bucket_name,
            db_alias=None  # Mongo db name for S3Index
    ):
        self.s3 = s3_instance
        self.bucket = bucket_name
        if db_alias:
            S3Index._meta["db_alias"] = db_alias

    @classmethod
    def _get_real_key(cls, entry: S3Index):
        if entry.data_info and entry.data_info.get("file_name"):
            return entry.data_info.get("file_name")
        return entry.id

    def _s3_multi_upload_action(self, action_type, action, name, key, *args, **kwargs):
        s3 = self.s3
        entry = S3Index.by_id(key)
        if entry:
            try:
                real_key = self._get_real_key(entry)
                result = action(name, real_key, *args, **kwargs)
                if action_type == ActionType.COMPLETE:
                    url = s3.url(self.bucket, real_key)
                    entry.after_uploaded(url)
                return result
            except Exception as e:
                entry.after_upload_failed(e)
                raise Exception(e)
        else:
            raise Exception("Can not find key %s in S3Index" % str(key))

    def _multi_upload_part(self, memory_file, s3_key, upload_id, part_num, ended, public):
        self.logger.info("Uploading object %s, part %d ..." % (s3_key, part_num))
        if part_num == 0:
            upload_id = self.initiate_multi_upload_raw_data(s3_key)
            self.logger.info("%s", "Multi uploading id %s" % upload_id)
        self.multi_upload_raw_data_part(s3_key, upload_id, part_num, memory_file)
        if ended:
            self.complete_multi_upload_raw_data(s3_key, upload_id, public)
            self.logger.info("Complete multi uploading")
        return upload_id

    def create_raw_data_info(self, data_info):
        entry = S3Index.create(data_info)
        return str(entry.id)

    def upload_raw_data_from_file(self, key, memory_file, public):
        data = memory_file.getvalue()
        part_num = 0
        upload_id = None
        while data:
            part = data[: self.MULTI_PART_SIZE_LIMIT_BYTES]
            data = data[self.MULTI_PART_SIZE_LIMIT_BYTES:]
            upload_id = self._multi_upload_part(
                part, key, upload_id, part_num, not data, public
            )
            part_num += 1

    def upload_from_file(self, key, file, public):
        part_num = 0
        upload_id = None
        while True:
            data = file.read(self.MULTI_PART_SIZE_LIMIT_BYTES)
            if not data:
                break
            upload_id = self._multi_upload_part(
                data,
                key,
                upload_id,
                part_num,
                len(data) < self.MULTI_PART_SIZE_LIMIT_BYTES,
                public,
            )
            part_num += 1

    def get_raw_data(self, key, fetching_url_expires_in=300):
        entry = S3Index.by_id(key)
        s3 = self.s3
        if entry:
            if entry.upload_success:
                return [True, s3.generate_fetching_url(self.bucket, self._get_real_key(entry),
                                                       expires_in=fetching_url_expires_in
                                                       )]
            elif entry.upload_failed:
                return [False, None]
            return [True, None]
        return [False, None]

    @classmethod
    def get_raw_data_info(cls, key):
        return S3Index.by_id(key)

    @classmethod
    def delete_raw_data(cls, key):
        entry = S3Index.by_id(key)
        if entry:
            entry.set_deleted()

    def initiate_multi_upload_raw_data(self, key):
        return self._s3_multi_upload_action(
            ActionType.INIT, self.s3.initiate_multipart_upload, self.bucket, key
        )

    def multi_upload_raw_data_part(self, key, upload_id, part_num, part):
        self._s3_multi_upload_action(
            ActionType.RUN,
            self.s3.upload_part_from_file, self.bucket, key, upload_id, part, part_num + 1
        )

    def complete_multi_upload_raw_data(self, key, upload_id, public):
        return self._s3_multi_upload_action(
            ActionType.COMPLETE,
            self.s3.complete_multipart_upload, self.bucket, key, upload_id, public=public
        )
