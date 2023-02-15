from typing import Collection, Any, List
from typing import TypeVar

T = TypeVar('T')


def x_prod(a: Collection[Any], b: Collection[Any], swap=False):
    """Returns the cross product of two lists.

    :param a: The first collection of elements.
    :param b: The second collection of elements.
    :param swap: If true, return both (x, y) and (y, x).
    """
    for x in a:
        for y in b:
            yield x, y
            if swap:
                yield y, x


def deduplicate(items: Collection[T]) -> List[T]:
    """Returns a deduplicated list of items, maintaining order."""
    seen = set()
    out = list()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def iter_batches(iterable, n=1):
    """Partition a collection into batches of size n."""
    length = len(iterable)
    for ndx in range(0, length, n):
        yield iterable[ndx:min(ndx + n, length)]
