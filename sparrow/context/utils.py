def expend_headers(header):
    """
    :param header: str
     e.g. 'Wish-Request-Id'
    :return: list
     e.g. ['Wish-Request-Id', 'wish-request-id', 'WishRequestId', 'wishrequestid', 'Wishrequestid']
    """
    rt = [header]
    header_lower = header.lower()
    rt.append(header_lower)
    words = header.split('-')
    rt.append(''.join(words))
    rt.append(rt[-1].lower())
    rt.append(rt[-1].capitalize())
    return rt


def get_header_value(headers, header_keys, default=None):
    return next(
            (headers.get(header) for header in header_keys if headers.get(header)),
            default
        )
