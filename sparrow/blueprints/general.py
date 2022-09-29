from flask import Blueprint

from sparrow.base.schema import Rsp
from sparrow.utils.os_utils import read_version
from sparrow.utils.request_utils import log_request_rate

general_bp = Blueprint('general', __name__, url_prefix='/api')


@general_bp.route('/health')
@log_request_rate(sample_rate=0)
def health():
    return Rsp(msg='I am OK').to_dict()


@general_bp.route('/pkg-version')
def version():
    v = read_version()
    return v or ''
