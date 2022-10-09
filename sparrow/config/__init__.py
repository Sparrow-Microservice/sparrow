import os
import glob

from sparrow.utils.os_utils import get_dir

CUR_DIR = get_dir(__file__)

server_config = [os.path.join(CUR_DIR, "settings.yaml")]


def get_secrets_files():
    secrets_dir = os.environ.get("WISH_FLASK_SECRETS_DIR", "/opt/vault/secrets")
    secrets_file_ext = os.environ.get("WISH_FLASK_SECRETS_FILE_EXT", "toml;yaml")
    exts = secrets_file_ext.split(";")
    ret = []
    for pat in ["*.{}".format(_) for _ in exts]:
        ret.extend(glob.glob(os.path.join(secrets_dir, pat)))
    return ret


def get_mongodb_secrets_file():
    secrets_dir = os.environ.get("WISH_FLASK_SECRETS_DIR", "/opt/vault/secrets")
    return secrets_dir


def get_builtin_config():
    """
    Get builtin config files. Now only support settings.yaml
    """
    return server_config
