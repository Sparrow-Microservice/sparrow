import boto3
import botocore
import botocore.exceptions
from io import StringIO

from wish_flask.lib.s3.abstract_s3 import BaseS3Abstraction
from wish_flask.lib.s3.s3_key import BaseS3Key
from wish_flask.utils.attr_utils import set_attr_from_config
from wish_flask.utils.iter_utils import keydict

# Not used, just for info
REGION_SETTINGS_MAP = {
    "us-west-1": {
        "host": "s3-us-west-1.amazonaws.com",
        "location": 'us-west-1'
    }, "cn-north-1": {
        "host": "s3.cn-north-1.amazonaws.com.cn",
        "location": 'cn-north-1',
    },
}


class RealS3Key(BaseS3Key):
    def __init__(self, object_summary, **kwargs):
        super().__init__(**kwargs)
        self._o = object_summary

    @property
    def bucket_name(self) -> str:
        return self._o.bukcet_name

    @property
    def key(self) -> str:
        return self._o.key

    @property
    def logical_key(self) -> str:
        if self._key_prefix:
            return self.key.replace(self._key_prefix, '')
        return self.key

    @property
    def data(self) -> str:
        return self.raw_data.decode('utf-8')

    @property
    def raw_data(self) -> bytes:
        return self._o.get()['Body'].read()


class RealS3(BaseS3Abstraction):

    CACHE_MAX_AGE = 3600 * 24

    def __init__(
            self,
            region_name="cn-north-1",
            *args,
            **kwargs
    ):
        self.region = region_name
        super().__init__(*args, **kwargs)

    def init_app(self, app, config=None):
        if config:
            set_attr_from_config(self, config, 'region', 'region_name')
        super().init_app(app, config=config)

    @property
    def client(self):
        return self.conn.meta.client

    def _get_key(self, name, key):
        full_name = self.get_bucket_name(name)
        key = self.get_key_name(key, name=name)
        _object = self.conn.Object(full_name, key)
        return _object

    def connect(self):
        if self.conn:
            return
        try:
            _session = boto3.Session(region_name=self.region)
            self.conn = _session.resource('s3')
        except:
            raise Exception("Connect S3 failed")

    def all_buckets(self):
        return keydict(self.conn.buckets.all(), lambda x: x.name)

    def initialize_bucket(self, full_name):
        try:
            config = {
                'LocationConstraint': self.region
            }
            webconfig = {
                'IndexDocument': {'Suffix': 'index.html'}
            }
            bucket = self.conn.create_bucket(
                Bucket=full_name, CreateBucketConfiguration=config)
            bucket.Website().put(WebsiteConfiguration=webconfig)
            return bucket
        except self.client.exceptions.BucketAlreadyExists as e:
            if e.reason != 'BucketAlreadyExists':
                raise

    def _get_bucket(self, name):
        full_name = self.get_bucket_name(name)
        return self.conn.Bucket(full_name)

    def iter_keys(self, name, prefix=None):
        bucket = self._get_bucket(name)
        key_prefix = self.get_key_name(prefix or '', name=name)
        params = {}
        if key_prefix:
            params['Prefix'] = key_prefix
        iterator = bucket.objects.filter(**params)
        raw_key_prefix = self.get_key_name('', name=name)
        for obj_summary in iterator:
            yield RealS3Key(
                obj_summary,
                logical_bucket_name=name,
                key_prefix=raw_key_prefix
            )

    def destroy_bucket(self, full_name):
        _bucket = self.conn.Bucket(full_name)
        _bucket.delete()

    def initiate_multipart_upload(self, name, key, content_type=None, cached=False):
        cache_control = ''
        if cached:
            cache_control = "max-age=%d, public" % self.CACHE_MAX_AGE

        full_name = self.get_bucket_name(name)
        key = self.get_key_name(key, name=name)
        if content_type:
            mpu = self.client.create_multipart_upload(
                Bucket=full_name, Key=key, CacheControl=cache_control, ContentType=content_type)
        else:
            mpu = self.client.create_multipart_upload(
                Bucket=full_name, Key=key, CacheControl=cache_control)
        return mpu["UploadId"]

    def upload_part_from_file(self, name, key, upload_id, bytes, part_num):
        key = self.get_key_name(key, name=name)
        full_name = self.get_bucket_name(name)
        mpup = self.conn.MultipartUploadPart(full_name, key, upload_id, part_num)
        try:
            mpup.upload(Body=bytes)
        except botocore.exceptions.ClientError as e:
            raise Exception("Check S3MultipartUploader IAM user policies: %s" % str(e))

    def complete_multipart_upload(self, name, key, upload_id, public=True):
        key = self.get_key_name(key, name=name)
        full_name = self.get_bucket_name(name)
        mpu = self.conn.MultipartUpload(full_name, key, upload_id)
        mpu_parts = self.client.list_parts(
            Bucket=full_name, Key=key, UploadId=upload_id)
        _parts = [
            {'ETag': p.get('ETag'), 'PartNumber': p.get('PartNumber')}
            for p in mpu_parts.get('Parts')
        ]
        parts = {
            'Parts': _parts
        }
        try:
            mpu.complete(MultipartUpload=parts)
        except Exception as e:
            raise Exception("Check S3MultipartUploader IAM user policies: %s" % str(e))
        if public:
            object_acl = self.conn.ObjectAcl(full_name, key)
            object_acl.put(ACL='public-read')

    def save(self, name, key, bytes, public=False, content_type=None, cached=False, stream=None):
        object = self._get_key(name, key)
        params = {}
        if content_type:
            params['ContentType'] = content_type
        if cached:
            if not isinstance(cached, int) or cached is True:
                cached = self.CACHE_MAX_AGE
            params['CacheControl'] = "max-age=%d, public" % cached
        if public:
            params['ACL'] = 'public-read'
        params['Body'] = stream or bytes

        object.put(**params)

    def save_stream(self, name, key, stream, public=False):
        return self.save(name, key, None, stream=stream, public=public)

    def load(self, name, key):  # type: (str, str) -> str
        return self.load_raw(name, key).decode('utf-8')

    def load_raw(self, name, key):  # type: (str, str) -> bytes
        _object = self._get_key(name, key)
        return _object.get()['Body'].read()

    def load_stream(self, name, key):
        return StringIO(self.load(name, key))

    def delete(self, name, key):
        _object = self._get_key(name, key)
        _object.delete()

    def url(self, name, key, try_cdn=True):
        # Url used to get the object. The requested object should have public-read ACL.
        key = self.get_key_name(key, name=name)
        host = self.host
        protocol = self.protocol + ':' if self.protocol else ""

        if try_cdn and name in self.cdn_names:
            return "%s//%s/%s" % (protocol, self.cdn_names[name], key)

        return "%s//%s/%s/%s" % (protocol, host, self.get_bucket_name(name), key)

    def generate_uploading_url(self,
                               name,
                               key,
                               acl=None,
                               content_type=None,
                               expires_in=300,
                               http_method="PUT"):
        params = {
            'Bucket': self.get_bucket_name(name),
            'Key': self.get_key_name(key, name=name)
        }
        if acl:
            params['ACL'] = acl
        if content_type:
            params['ContentType'] = content_type
        return self.client.generate_presigned_url(
            ClientMethod='put_object',
            Params=params,
            ExpiresIn=expires_in,
            HttpMethod=http_method
        )

    def generate_fetching_url(self, name, key, expires_in=3600):
        key = self.get_key_name(key, name=name)
        full_name = self.get_bucket_name(name)

        url = self.client.generate_presigned_url(
            ExpiresIn=expires_in,
            ClientMethod="get_object",
            Params={'Bucket': full_name, 'Key': key}
        )
        return url

    def exists(self, name, key):
        try:
            _object = self._get_key(name, key)
            _object.last_modified
        except botocore.exceptions.ClientError as e:
            return False
        return True

    def last_modified(self, name, key):
        _object = self._get_key(name, key)
        modified_stamp = int(_object.last_modified.timestamp())
        return modified_stamp

    def get_size(self, name, key):
        _object = self._get_key(name, key)
        return _object.content_length

    def copy(self, ori_name, ori_key, dst_name, dst_key, preserve_acl=True, delete_origin=True):
        _source = {
            'Bucket': self.get_bucket_name(ori_name),
            'Key': self.get_key_name(ori_key, name=ori_name)
        }
        dst_object = self._get_key(dst_name, dst_key)
        try:
            dst_object.copy(_source)
        except Exception:
            return ""

        if preserve_acl:
            ori_acl = self._get_key(ori_name, ori_key).Acl()
            dst_acl = dst_object.Acl()
            dst_acl.put(AccessControlPolicy={
                'Grants': ori_acl.grants,
                'Owner': ori_acl.owner
            })

        if delete_origin:
            self.delete(ori_name, ori_key)

        return self.url(dst_name, dst_key)
