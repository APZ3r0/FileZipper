"""Tiny helper functions for zipping a folder and dropping a copy elsewhere."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path


def _clean_path(raw: Path) -> Path:
    path = Path(raw).expanduser()
    return path.resolve()


def create_zip(source: Path, output: Path | None = None) -> Path:
    """Create a ZIP file containing *source* and return the archive path."""

    src = _clean_path(source)
    if not src.exists():
        raise FileNotFoundError(f"Cannot find: {source}")

    zip_name = f"{src.name}.zip"

    if output is None:
        archive_path = src.parent / zip_name
    else:
        candidate = Path(output).expanduser()
        if candidate.suffix:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            archive_path = candidate
        else:
            destination_dir = _clean_path(candidate)
            destination_dir.mkdir(parents=True, exist_ok=True)
            archive_path = destination_dir / zip_name

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if src.is_file():
            zf.write(src, arcname=src.name)
        else:
            contains_files = False
            for item in sorted(src.rglob("*")):
               https://github.com/APZ3r0/FileZipper/pull/6/conflict?name=pyproject.toml&base_oid=0a8012ac3ab31d6bfdc23b3c782a4de6a4e10a5c&head_oid=460ce75c4cbcd866dae3b1ab67795da0949ce38d if item.is_file():
                    contains_files = True
                    arcname = item.relative_to(src)
                    zf.write(item, arcname=str(Path(src.name) / arcname))
            if not contains_files:
                zf.writestr(f"{src.name}/", "")

    return archive_path.resolve()


def make_copy(archive: Path, destination: Path) -> Path:
    """Copy *archive* to *destination* and return where it landed."""

    archive_path = _clean_path(archive)
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive}")

    target = Path(destination).expanduser()
    if target.is_dir() or (not target.exists() and target.suffix == ""):
        target.mkdir(parents=True, exist_ok=True)
        copy_path = target / archive_path.name
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        copy_path = target

    shutil.copy2(archive_path, copy_path)
    return copy_path.resolve()


__all__ = ["create_zip", "make_copy"]
"""Core functionality for creating ZIP archives and copying them to destinations."""

from __future__ import annotations

import datetime as _dt
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class ArchiveEntry:
    """Represents a file that will be written to the archive."""

    source: Path
    arcname: Path


def _is_hidden(path: Path) -> bool:
    """Return ``True`` if any part of *path* starts with a dot."""

    return any(part.startswith(".") for part in path.parts)


def _normalize_sources(sources: Sequence[Path]) -> List[Path]:
    resolved: List[Path] = []
    for src in sources:
        path = Path(src).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Source path does not exist: {src}")
        resolved.append(path)
    return resolved


def _gather_entries(path: Path, include_hidden: bool) -> Iterable[ArchiveEntry]:
    if path.is_file():
        yield ArchiveEntry(source=path, arcname=Path(path.name))
        return

    root_name = Path(path.name)
    for item in sorted(path.rglob("*")):
        if not item.is_file():
            continue
        relative = item.relative_to(path)
        if not include_hidden and _is_hidden(relative):
            continue
        yield ArchiveEntry(source=item, arcname=root_name / relative)


def _timestamped_name() -> str:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"archive-{stamp}.zip"


def create_archive(
    sources: Sequence[Path],
    output: Path | None = None,
    include_hidden: bool = False,
    compression: int = zipfile.ZIP_DEFLATED,
) -> Path:
    """Create a ZIP archive containing *sources*.

    Parameters
    ----------
    sources:
        Paths (files or directories) that should be included in the archive.
    output:
        Optional output file path. If a directory is provided the archive will
        be created inside that directory using a timestamped file name. When
        omitted, the archive is written to the current working directory using
        a timestamped file name.
    include_hidden:
        If ``True`` hidden files and directories (those beginning with ``.``)
        are included when traversing directories.
    compression:
        Compression method to use for the archive. ``zipfile.ZIP_DEFLATED`` is
        used by default, which requires zlib support (available in the Python
        standard library).

    Returns
    -------
    Path
        The location of the archive that was created.
    """

    if not sources:
        raise ValueError("At least one source path must be provided.")

    normalized = _normalize_sources(list(sources))

    if output is None:
        output_path = Path.cwd() / _timestamped_name()
    else:
        candidate = Path(output).expanduser()
        if candidate.exists() and candidate.is_dir():
            candidate.mkdir(parents=True, exist_ok=True)
            output_path = candidate / _timestamped_name()
        elif not candidate.exists() and candidate.suffix == "":
            candidate.mkdir(parents=True, exist_ok=True)
            output_path = candidate / _timestamped_name()
        else:
            candidate.parent.mkdir(parents=True, exist_ok=True)
            output_path = candidate

    output_path = output_path.resolve()

    entries: List[ArchiveEntry] = []
    for src in normalized:
        if src.is_dir():
            entries.extend(list(_gather_entries(src, include_hidden=include_hidden)))
        else:
            arcname = Path(src.name)
            entries.append(ArchiveEntry(source=src, arcname=arcname))

    with zipfile.ZipFile(output_path, "w", compression=compression) as zf:
        for entry in entries:
            zf.write(entry.source, arcname=str(entry.arcname))

    return output_path


def copy_to_locations(archive_path: Path, destinations: Sequence[Path]) -> List[Tuple[Path, Path]]:
    """Copy *archive_path* to each directory in *destinations*.

    Returns a list of tuples containing ``(destination_directory, copied_file)``.
    """

    archive = Path(archive_path).expanduser().resolve()
    if not archive.exists():
        raise FileNotFoundError(f"Archive does not exist: {archive_path}")

    results: List[Tuple[Path, Path]] = []
    for dest in destinations:
        target = Path(dest).expanduser()
        if target.exists() and target.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            copied_path = target
        elif not target.exists() and target.suffix:
            target.parent.mkdir(parents=True, exist_ok=True)
            copied_path = target
        else:
            target.mkdir(parents=True, exist_ok=True)
            copied_path = target / archive.name
        copied_path = copied_path.resolve()
        shutil.copy2(archive, copied_path)
        results.append((copied_path.parent, copied_path))
    return results
