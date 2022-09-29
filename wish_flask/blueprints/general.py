from flask import Blueprint

from wish_flask.base.schema import Rsp
from wish_flask.utils.os_utils import read_version
from wish_flask.utils.request_utils import log_request_rate

general_bp = Blueprint('general', __name__, url_prefix='/api')


@general_bp.route('/health')
@log_request_rate(sample_rate=0)
def health():
    return Rsp(msg='I am OK').to_dict()


@general_bp.route('/pkg-version')
def version():
    v = read_version()
    return v or ''
