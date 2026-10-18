"""minigit count-objects: report the count and disk consumption of objects."""

from __future__ import annotations

import os
import re
import stat
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from minigit.repo import Repository

NAME = "count-objects"
HELP = "Count unpacked number of objects and their disk consumption"

_HEX_2 = re.compile(r"^[0-9a-f]{2}$")
_HEX_38 = re.compile(r"^[0-9a-f]{38}$")


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="be verbose",
    )


def _on_disk_bytes(st: os.stat_result) -> int:
    """Mirror Git's on_disk_bytes() macro from git-compat-util.h.

    Where st_blocks exists (POSIX), Git uses st_blocks * 512 bytes.
    Where it doesn't (Windows), Git uses st.st_size bytes.
    """
    blocks = getattr(st, "st_blocks", None)
    if blocks is None:
        return st.st_size
    return blocks * 512


def run(args: argparse.Namespace, repo: Repository) -> int:
    objects_dir = repo.gitdir / "objects"
    count = 0
    total_bytes = 0

    if objects_dir.is_dir():
        for subdir in objects_dir.iterdir():
            if subdir.is_dir() and _HEX_2.fullmatch(subdir.name):
                for obj_file in subdir.iterdir():
                    if not _HEX_38.fullmatch(obj_file.name):
                        continue
                    st = obj_file.lstat()
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    count += 1
                    total_bytes += _on_disk_bytes(st)

    size_kib = total_bytes // 1024
    if args.verbose:
        print(f"count: {count}")
        print(f"size: {size_kib}")
    else:
        print(f"{count} objects, {size_kib} kilobytes")

    return 0
