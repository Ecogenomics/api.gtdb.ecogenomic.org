import csv
import hashlib
import io

from fastapi import UploadFile

from api.exceptions import HttpBadRequest


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


def string_size_in_mb(string: str) -> float:
    """Converts a string to a size in MB."""
    return len(string.encode('utf-8')) / (1024 * 1024)


def sha256(string: str) -> str:
    """Returns the SHA256 hash of a string."""
    return hashlib.sha256(string.encode('utf-8')).hexdigest()


async def read_upload_file_bytes_limit(uploaded_file: UploadFile, bytes_limit: int) -> str:
    """Read an UploadFile and throw an error if it exceeds the byte limit. Also output the sha256 hash."""
    total_bytes = 0
    contents = bytearray()
    chunk_size = 1024 * 1024  # 1 MB
    while True:
        chunk = await uploaded_file.read(chunk_size)
        if not chunk:
            break
        contents.extend(chunk)
        total_bytes += len(chunk)
        if total_bytes > bytes_limit:
            raise HttpBadRequest(f'File {uploaded_file.filename} exceeds the size limit of {sizeof_fmt(bytes_limit)}.')
    return contents.decode('utf-8')


def iter_triangle(values: list, diagonal: bool = True):
    """Iterate over the upper triangle of a square matrix."""
    offset = 0 if diagonal else 1
    n = len(values)
    for i in range(n):
        for j in range(i+offset, n):
            yield values[i], values[j]
