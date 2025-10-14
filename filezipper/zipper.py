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
                if item.is_file():
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
