import unittest
from dataclasses import dataclass
import inspect


@dataclass
class HelloRequest:
    name: str


@dataclass
class HelloResponse:
    msg: str


def hello(req: HelloRequest) -> HelloResponse:
    return HelloResponse(msg=f'hello {req.name}')

import typing


class Hello:
    _blp = None

    def __init__(self):
        self._blp = 123

class MyTestCase(unittest.TestCase):
    def test_something(self):
        a = Hello()
        print("zzzzzzzz", a._blp, Hello._blp)





if __name__ == '__main__':
    unittest.main()
