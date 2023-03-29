import re

def is_int(value: any) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False

def is_valid_email(value: any) -> bool:
    if value is None or not isinstance(value, str):
        return False
    if len(value) > 320:
        return False
    re_match = re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", value)
    return re_match is not None
