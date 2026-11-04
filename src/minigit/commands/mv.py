"""minigit mv: move or rename a file, a directory, or a symlink.

    minigit mv notes.txt docs/notes.txt
    minigit mv notes.txt docs/
    minigit mv src new_src

Renames or moves a tracked file on disk and updates the staging area.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

from minigit.errors import MinigitError
from minigit.index import Index, IndexEntry
from minigit.repo import Repository
from minigit.worktree import repo_relative

NAME = "mv"
HELP = "Move or rename a file, a directory, or a symlink"


def configure(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="force move/rename even if target exists",
    )
    parser.add_argument("source", help="source file or directory")
    parser.add_argument("destination", help="destination file or directory")


def run(args: argparse.Namespace, repo: Repository | None) -> int:
    assert repo is not None

    raw_src = args.source
    raw_dest = args.destination

    src_rel = repo_relative(repo, raw_src)
    dest_rel = repo_relative(repo, raw_dest)

    index = Index.load(repo)
    src_entry = index.get(src_rel)
    dir_entries = [e for e in index if e.path.startswith(f"{src_rel}/")]

    src_disk = repo.worktree / src_rel
    dest_disk = repo.worktree / dest_rel

    # 1. Source existence check
    if not src_disk.exists():
        raise MinigitError(f"bad source, source={raw_src}, destination={raw_dest}")

    # 2. Source tracked check
    if src_entry is None and not dir_entries:
        raise MinigitError(f"not under version control, source={raw_src}, destination={raw_dest}")

    is_dir = src_disk.is_dir()
    ends_with_slash = raw_dest.endswith("/") or raw_dest.endswith("\\")

    # 3. Check for destination directory syntax on non-existent directory
    if ends_with_slash and not is_dir and not dest_disk.is_dir():
        raise MinigitError(
            f"destination directory does not exist, source={raw_src}, destination={raw_dest}"
        )

    # 4. Determine destination target
    dest_was_dir = dest_disk.is_dir()
    if dest_was_dir:
        target_name = Path(src_rel).name
        dest_sub_rel = f"{dest_rel}/{target_name}" if dest_rel else target_name
    else:
        dest_sub_rel = dest_rel

    # 5. Cannot move directory or file into itself
    if dest_sub_rel == src_rel or (is_dir and dest_sub_rel.startswith(f"{src_rel}/")):
        raise MinigitError(
            f"can not move directory into itself, source={raw_src}, destination={raw_dest}"
        )

    # 6. Check destination collisions if not forced
    if is_dir:
        target_dir = repo.worktree / dest_sub_rel
        if target_dir.exists() and not args.force:
            raise MinigitError(
                f"destination already exists, source={raw_src}, destination={dest_sub_rel}"
            )
        moves = [(e.path, f"{dest_sub_rel}{e.path[len(src_rel) :]}") for e in dir_entries]
        if not args.force:
            for _, d_path in moves:
                if (repo.worktree / d_path).exists() or d_path in index:
                    raise MinigitError(
                        f"destination exists, source={raw_src}, destination={d_path}"
                    )
    else:
        target_file = repo.worktree / dest_sub_rel
        is_case_change = (
            sys.platform == "win32"
            and src_rel != dest_sub_rel
            and src_rel.lower() == dest_sub_rel.lower()
        )
        if not is_case_change and not args.force:
            if target_file.exists() or dest_sub_rel in index:
                clean_dest = raw_dest.rstrip("/\\")
                dest_display = f"{clean_dest}/{Path(src_rel).name}" if dest_was_dir else raw_dest
                raise MinigitError(
                    f"destination exists, source={raw_src}, destination={dest_display}"
                )
        moves = [(src_rel, dest_sub_rel)]

    # 7. Move on disk
    if is_dir:
        target_dir = repo.worktree / dest_sub_rel
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        if not target_dir.exists():
            shutil.move(str(src_disk), str(target_dir))
        else:
            for root, dirs, files in os.walk(src_disk, topdown=False):
                rel_root = Path(root).relative_to(src_disk)
                dest_root = target_dir / rel_root
                dest_root.mkdir(parents=True, exist_ok=True)
                for f in files:
                    s_file = Path(root) / f
                    d_file = dest_root / f
                    if d_file.exists():
                        d_file.unlink()
                    os.replace(s_file, d_file)
                for d in dirs:
                    try:
                        (Path(root) / d).rmdir()
                    except OSError:
                        pass
            try:
                src_disk.rmdir()
            except OSError:
                pass
    else:
        target_file = repo.worktree / dest_sub_rel
        target_file.parent.mkdir(parents=True, exist_ok=True)
        if target_file.exists() and args.force and target_file != src_disk:
            target_file.unlink()
        os.replace(src_disk, target_file)

    # 8. Update index
    for s_path, d_path in moves:
        entry = index.get(s_path)
        if entry is not None:
            index.remove(s_path)
            index.add(IndexEntry(entry.mode, entry.sha, d_path))

    index.save(repo)
    return 0
