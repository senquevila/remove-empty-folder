"""Core logic: detect and remove directories with no real files."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .config import IGNORED_EXTENSIONS, IGNORED_PREFIXES


@dataclass
class Candidate:
    """A directory that holds no real files and can be removed."""

    path: Path
    ignored_files: list[Path] = field(default_factory=list)
    subdirs: int = 0  # number of nested (also empty) subdirectories


def is_ignorable(
    name: str,
    extensions: Iterable[str] = IGNORED_EXTENSIONS,
    prefixes: Iterable[str] = IGNORED_PREFIXES,
) -> bool:
    """Return True when a file name matches an ignored extension or prefix."""
    lower = name.lower()
    return any(lower.endswith(ext.lower()) for ext in extensions) or any(
        name.startswith(p) for p in prefixes
    )


def _visit(
    directory: Path,
    extensions: tuple[str, ...],
    found: list[Candidate],
    is_root: bool,
    on_dir: Callable[[Path], None] | None = None,
    recursive: bool = True,
) -> Candidate | None:
    """Walk ``directory``; return a Candidate if it is removable.

    Removable children of a non-removable directory are appended to ``found``,
    so only the top-most removable directories are reported. With
    ``recursive=False`` only root's direct children can be reported, so a
    non-root directory stops walking at its first real content.
    """
    stop_early = not (recursive or is_root)
    if on_dir:
        on_dir(directory)
    removable = True
    ignored: list[Path] = []
    subdirs = 0
    children: list[Candidate] = []

    try:
        entries = sorted(os.scandir(directory), key=lambda e: e.name.lower())
    except OSError:
        return None  # unreadable: never touch it

    for entry in entries:
        if stop_early and not removable:
            return None
        if entry.is_symlink():
            removable = False  # never follow or delete through symlinks
            continue
        if entry.is_dir(follow_symlinks=False):
            child = _visit(Path(entry.path), extensions, found, False, on_dir, recursive)
            if child is None:
                removable = False
            else:
                children.append(child)
        elif not removable:
            continue  # already has real content; only subdirs still matter
        elif is_ignorable(entry.name, extensions):
            ignored.append(Path(entry.path))
        else:
            removable = False

    if stop_early and not removable:
        return None
    if removable and not is_root:
        for child in children:
            ignored.extend(child.ignored_files)
            subdirs += 1 + child.subdirs
        return Candidate(directory, ignored, subdirs)

    found.extend(children)
    return None


def scan(
    root: str | Path,
    extensions: tuple[str, ...] = IGNORED_EXTENSIONS,
    progress: Callable[[Path, int, int, int], None] | None = None,
    recursive: bool = True,
) -> list[Candidate]:
    """Return the top-most removable directories under ``root`` (root excluded).

    With ``recursive=False`` only root's direct subdirectories are reported.

    ``progress(current_dir, top_done, top_total, dirs_seen)`` is called for every
    directory visited. Progress is measured over root's direct subdirectories,
    since the full tree size is unknown until the walk ends.
    """
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    on_dir = None
    if progress:
        try:
            total = sum(e.is_dir(follow_symlinks=False) for e in os.scandir(root))
        except OSError:
            total = 0
        done = seen = 0

        def on_dir(path: Path) -> None:
            nonlocal done, seen
            seen += 1
            if path.parent == root:
                done += 1
            progress(path, done, total, seen)

    found: list[Candidate] = []
    _visit(root, tuple(extensions), found, True, on_dir, recursive)
    return sorted(found, key=lambda c: str(c.path).lower())


def is_removable(path: str | Path, extensions: tuple[str, ...] = IGNORED_EXTENSIONS) -> bool:
    """Re-check a single directory right before deleting it."""
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        return False
    return _visit(path, tuple(extensions), [], False, recursive=False) is not None


def remove(path: str | Path, extensions: tuple[str, ...] = IGNORED_EXTENSIONS) -> bool:
    """Delete ``path`` if it is still removable. Returns True when deleted."""
    if not is_removable(path, extensions):
        return False
    shutil.rmtree(path)
    return True
