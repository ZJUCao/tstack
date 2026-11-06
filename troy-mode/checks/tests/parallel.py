"""A small helper that runs independent checker invocations concurrently."""

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, List, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def parallel(func: Callable[[T], R], items: Iterable[T], workers: int = 6) -> List[R]:
    """Applies a function to every item in a thread pool.

    Each call starts its own subprocesses, so threads give a real speed-up.
    The result order matches the item order.

    Args:
        func: Function of one argument.
        items: The arguments.
        workers: Maximum number of concurrent calls.

    Returns:
        The results, in item order.
    """
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(func, items))
