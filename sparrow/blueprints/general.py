from sparrow.base.blueprint import Blueprint

from sparrow.utils.os_utils import read_version
from sparrow.utils.request_utils import log_request_rate

general_bp = Blueprint('general', __name__, url_prefix='/api')


@general_bp.route('/health')
@log_request_rate(sample_rate=0)
def health():
    return {
        "code": 200,
        "msg": "I am OK",
        "data": "",
    }


@general_bp.route('/pkg-version')
def version():
    v = read_version()
    return v or ''
