import re


def _to_camel_one(component, capital_first=True, lower_rest=True):
    first = component[0] if len(component) > 0 else ''
    rest = component[1:]
    if capital_first:
        first = first.upper()
    if lower_rest:
        rest = rest.lower()
    return first + rest


def to_camel_case(
        snake_str,
        capital_first=True,  # Capitalize the first letter of first component
        lower_rest=True  # lower the rest letters for each component
):
    """
    >>> to_camel_case('abc_def', capital_first=True, lower_rest=True)
    'AbcDef'

    >>> to_camel_case('abcdef', capital_first=True, lower_rest=True)
    'Abcdef'

    >>> to_camel_case('aBC_deF', capital_first=True, lower_rest=True)
    'AbcDef'

    >>> to_camel_case('a_bc_def', capital_first=True, lower_rest=True)
    'ABcDef'

    >>> to_camel_case('a_bc_dEf', capital_first=False, lower_rest=True)
    'aBcDef'

    >>> to_camel_case('a_bc_dEf', capital_first=True, lower_rest=False)
    'ABcDEf'
    """
    components = snake_str.split('_')
    return _to_camel_one(components[0], capital_first=capital_first, lower_rest=lower_rest) + \
        ''.join(_to_camel_one(x, True, lower_rest=lower_rest) for x in components[1:])


def to_snake_case(camel_str):
    """
    >>> to_snake_case('AbcDef')
    'abc_def'

    >>> to_snake_case('ABCDEF')
    'abcdef'

    >>> to_snake_case('ABcDef')
    'a_bc_def'

    >>> to_snake_case('ABCDef')
    'abc_def'
    """
    name = re.sub('([A-Z]+)([A-Z][a-z])', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()


def json_decode(obj):
    import ujson
    return ujson.decode(obj)
