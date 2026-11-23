"""Lock files around writes that several hook processes make at once (F20 design 3.3).

Roles of several teams, and one role's calls in parallel, run hook processes
at the same time. On Windows, appends to one file from several processes
lose lines, and a record's read-change-save loses updates (F20 design
section 2). A lock is a file beside the one written, made exclusively.
"""

import contextlib
import os
import time

SUFFIX = ".lock"
WAIT = 1.0      # seconds a writer tries for the lock before it writes without it
STEP = 0.01     # seconds between tries
STALE = 10.0    # seconds after which a lock file is taken over


def _take(lock: str, wait: float) -> bool:
    """Makes the lock file; False when another writer still held it after the wait."""
    os.makedirs(os.path.dirname(lock) or ".", exist_ok=True)
    deadline = time.monotonic() + wait
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return True
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > STALE:
                    os.remove(lock)
                    continue
            except OSError:
                pass
        except OSError:
            pass  # Windows refuses a file that another process is deleting
        if time.monotonic() >= deadline:
            return False
        time.sleep(STEP)


@contextlib.contextmanager
def held(path: str, wait: float = WAIT):
    """Holds <path>.lock while the block runs.

    After the wait the block runs without the lock, so a lock that nobody
    releases delays a hook call by about a second and never stops it. A
    lock file older than STALE seconds is taken over.

    Args:
        path: The file the block writes.
        wait: Seconds to try for the lock.
    """
    lock = path + SUFFIX
    got = _take(lock, wait)
    try:
        yield got
    finally:
        if got:
            with contextlib.suppress(OSError):
                os.remove(lock)
