

def is_int(value: str):
    try:
        return True, int(value)
    except ValueError:
        return False, value


def is_hexadecimal(value: str):
    try:
        return True, int(value, 16)
    except ValueError:
        return False, value
