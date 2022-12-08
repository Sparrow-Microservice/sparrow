import os

from sparrow.utils.os_utils import get_dir

CUR_DIR = get_dir(__file__)

server_config = [os.path.join(CUR_DIR, "settings.yaml")]
