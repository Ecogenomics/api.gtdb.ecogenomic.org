from api import __version__
from api.model.meta import MetaVersionResponse


def get_meta_version() -> MetaVersionResponse:
    major, minor, patch = __version__.split('.')
    major, minor, patch = int(major), int(minor), int(patch)
    return MetaVersionResponse(major=major, minor=minor, patch=patch)
