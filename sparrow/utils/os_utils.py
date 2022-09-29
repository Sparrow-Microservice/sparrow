import os
import sys

PY3 = sys.version_info.major == 3

CUR_DIR = os.path.dirname(__file__)


def get_dir(file):
    return os.path.abspath(os.path.dirname(file))


def read_file(path, **kwargs):
    with open(path, **kwargs) as open_file:
        content = open_file.read().strip()
    return content


def read_file_in_root_directory(*names, **kwargs):
    """Read a file on root dir."""
    if PY3:
        kwargs.setdefault("encoding", "utf-8")
    return read_file(
        os.path.join(os.path.dirname(CUR_DIR), *names),
        **kwargs
    )


def read_version():
    return read_file_in_root_directory('VERSION')
