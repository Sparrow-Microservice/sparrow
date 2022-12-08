from sparrow.base import Blueprint
from dataclasses import dataclass

hello_blp = Blueprint('hello', __name__, url_prefix='/api/hello', description='Operation on hello')


@dataclass
class HelloRequest:
    name: str


@dataclass
class HelloResponse:
    msg: str


@hello_blp.route('/', methods=['POST'])
@hello_blp.arguments(HelloRequest)
@hello_blp.response(data_clz=HelloResponse)
def hello(req: HelloRequest):
    return HelloResponse(msg=f'hello {req.name}')
