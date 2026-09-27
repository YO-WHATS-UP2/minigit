"""Working out who is making a commit, and when."""

from __future__ import annotations

import os
import time

from minigit.errors import MinigitError
from minigit.objects import Signature

DEFAULT_NAME = "Anonymous"
DEFAULT_EMAIL = "anonymous@example.com"


def format_tz(offset_seconds: int) -> str:
    """Turn a UTC offset in seconds into Git's ``+HHMM`` form (19800 -> ``"+0530"``)."""
    sign = "+" if offset_seconds >= 0 else "-"
    minutes = abs(offset_seconds) // 60
    return f"{sign}{minutes // 60:02d}{minutes % 60:02d}"


def author_signature() -> Signature:
    """Return the signature for a new commit.

    Reads these environment variables:

    * ``MINIGIT_AUTHOR_NAME`` and ``MINIGIT_AUTHOR_EMAIL``
    * ``MINIGIT_AUTHOR_DATE`` as ``"<unix timestamp> <+HHMM>"``, which pins
      the time so tests produce the same SHAs on every run
    """
    name = os.environ.get("MINIGIT_AUTHOR_NAME") or DEFAULT_NAME
    email = os.environ.get("MINIGIT_AUTHOR_EMAIL") or DEFAULT_EMAIL
    date = os.environ.get("MINIGIT_AUTHOR_DATE")
    if date:
        try:
            timestamp, tz = date.split()
            return Signature.parse(f"{name} <{email}> {int(timestamp)} {tz}")
        except ValueError:
            raise MinigitError(f"invalid MINIGIT_AUTHOR_DATE: {date!r}") from None
    timestamp = int(time.time())
    return Signature(name, email, timestamp, format_tz(time.localtime(timestamp).tm_gmtoff))
