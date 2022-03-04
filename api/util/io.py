import io
import csv


def sizeof_fmt(num: float, suffix='B') -> str:
    """Convert bytes to human-readable units.
    https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
    """
    try:
        for unit in ('', 'K', 'M', 'G', 'T', 'P', 'E', 'Z'):
            if abs(num) < 1000:
                return f'{num:3.1f} {unit}{suffix}'
            num /= 1000
        return f'{num:.1f} Y{suffix}'
    except Exception:
        return 'N/A'


def rows_to_delim(rows: list, delim: str = ',') -> str:
    """Converts a collection of rows to a string."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, delimiter=delim)
    for row in rows:
        writer.writerow(row)
    return output.getvalue()
