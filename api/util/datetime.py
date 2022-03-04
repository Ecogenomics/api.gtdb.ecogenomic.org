from datetime import datetime
from typing import Optional


def dt_to_str(dt: Optional[datetime]) -> Optional[str]:
    """Converts a datetime object to the expected string format if present."""
    return dt if not dt else dt.strftime('%Y-%m-%dT%H:%M:%S')


def str_to_dt(dt: Optional[str]) -> Optional[datetime]:
    """Converts a string object to the expected datetime format if present."""
    if not dt:
        return dt
    try:
        dt_obj = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
    except ValueError:
        dt_obj = datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f')
    return dt_obj.replace(microsecond=0)
