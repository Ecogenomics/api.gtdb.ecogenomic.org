import functools
import hashlib
import pickle
import re
import time
from pathlib import Path
from typing import Any, Callable, Tuple

from fastapi import Request

from api.config import CACHE_DIR
from api.exceptions import HttpBaseException

RE_UNSAFE_CHARACTERS = re.compile(r'[\\/*?:"<>|]')


def escape_for_disk(s: str) -> str:
    return RE_UNSAFE_CHARACTERS.sub('_', s)


def md5_string(s: str) -> str:
    hash_object = hashlib.md5()
    hash_object.update(s.encode('utf-8'))
    return hash_object.hexdigest()


def get_cache_key_from_request(request: Request) -> Tuple[str, str, str | None]:
    """
    Generate a unique cache key for the request based on the request.
    The query is sorted to ensure results are cached regardless of the order.
    """
    method = request.method
    path = request.url.path
    if request.url.query:
        query = '&'.join(sorted(request.url.query.split('&')))
    else:
        query = None
    return method, path, query


def get_cache_path_from_request(request: Request) -> Path | None:
    if not CACHE_DIR:
        return None
    method, path, query = get_cache_key_from_request(request)

    # Generate the hash for the full request
    key = f'{method}__{path}__{query}'
    md5 = md5_string(key)

    # Get the parent directory to store the cached file
    root_dir = CACHE_DIR / md5[0:2] / md5[2:4] / md5[4:6]
    file_path = root_dir / f'{escape_for_disk(key)}__{md5}.pkl'
    return file_path


def cached(ttl: int, disk: bool = False) -> Callable:
    # For ttl values less than 0, we want to use the maximum value (1 year)
    if ttl < 0:
        ttl = 31536000

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def func_wrapper(*args: tuple[Any], **kwargs: dict[str, Any]) -> Any:

            # Extract the required information
            response = kwargs.get('response')
            request = kwargs.get('request')

            # Update the response with the cache control header if set
            if response:
                response.headers["Cache-Control"] = f'max-age={ttl}, must-revalidate, proxy-revalidate'

            # Exit early if we do not care about disk caching
            if not disk:
                return await func(*args, **kwargs)

            # From here on we expect the request to be present, and disk caching
            if not request:
                print(f'Warning: Call made to a cached method without request being set.')
                return await func(*args, **kwargs)

            # Obtain the cache path
            cache_path = get_cache_path_from_request(request)
            if not cache_path:
                print(f'Warning: CACHE_DIR not set in .env')
                return await func(*args, **kwargs)

            # Check if the result already exists
            if cache_path.exists():

                # Check the age
                file_age = int(time.time() - cache_path.stat().st_ctime)

                # The cache is still valid
                if file_age < ttl:
                    with cache_path.open('rb') as f:
                        result = pickle.load(f)

                    # Either raise or return based on the type of result
                    if isinstance(result, HttpBaseException):
                        result.headers = {
                            'Cache-Control': 'max-age=60, must-revalidate, proxy-revalidate',
                            'X-API-Cached': 'true',
                            'X-API-Age': str(file_age)
                        }
                        raise result
                    else:
                        # Update the response headers with the max-age cache control
                        response.headers["Cache-Control"] = f'max-age={ttl}, must-revalidate, proxy-revalidate'
                        response.headers["X-API-Cached"] = 'true'
                        response.headers["X-API-Age"] = str(file_age)

                        return result

            # Otherwise, run the endpoint
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                if isinstance(e, HttpBaseException) and e.status_code < 500:
                    result = e
                else:
                    raise

            # Write the result to disk
            cache_path.parent.mkdir(exist_ok=True, parents=True)
            with cache_path.open('wb') as f:
                pickle.dump(result, f)

            # Either return or raise depending on the result status code
            if isinstance(result, HttpBaseException):
                result.headers = {
                    'Cache-Control': 'max-age=60, must-revalidate, proxy-revalidate',
                    'X-API-Cached': 'true',
                    'X-API-Age': '0'
                }
                raise result
            else:
                # Update the response headers with the max-age cache control
                response.headers["Cache-Control"] = f'max-age={ttl}, must-revalidate, proxy-revalidate'
                response.headers["X-API-Cached"] = 'true'
                response.headers["X-API-Age"] = '0'
                return result

        return func_wrapper

    return decorator
