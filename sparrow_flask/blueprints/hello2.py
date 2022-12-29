from sparrow_flask.base.application import Sparrow
from dataclasses import dataclass


@dataclass
class HelloRequest2:
    name: str


@dataclass
class HelloResponse2:
    msg: str


@Sparrow.arguments(HelloRequest2)
@Sparrow.response(data_clz=HelloResponse2)
def hello2(req: HelloRequest2):
    return HelloResponse2(msg=f'hello {req.name}')
