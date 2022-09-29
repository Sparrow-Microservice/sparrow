# -*- coding: utf-8 -*-
from {{cookiecutter.project_name_snake}}.__tests__.utils import my_max, my_min


def test_max():
    a = 10
    b = 2
    val = my_max(a, b)
    assert a == val

def test_min():
    a = 10
    b = 2
    val = my_min(a, b)
    assert b == val
