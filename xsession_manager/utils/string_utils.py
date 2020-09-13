
def empty_string(string):
    """
    Check a string is blank, None or not
    :param string:
    :return:
    """
    return string in (None, '') or not string.strip()

