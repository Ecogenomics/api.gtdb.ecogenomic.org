def is_int(value: any) -> bool:
    try:
        int(value)
        return True
    except ValueError:
        return False
