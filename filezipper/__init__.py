"""Simple helpers for zipping a folder and making a backup copy."""

from .zipper import create_zip, make_copy

__all__ = ["create_zip", "make_copy"]
"""Utilities for creating ZIP archives and copying them to storage targets."""

from .zipper import create_archive, copy_to_locations

__all__ = ["create_archive", "copy_to_locations"]
