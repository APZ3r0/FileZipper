from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import unittest
from unittest import mock

import tkinter as tk

from filezipper.zipper import copy_to_locations, create_archive
from filezipper import gui


class FileZipperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def _create_structure(self) -> None:
        (self.root / "docs").mkdir()
        (self.root / "docs" / "notes.txt").write_text("meeting notes")
        (self.root / "docs" / ".secret.txt").write_text("hidden")
        (self.root / "readme.md").write_text("# Project")

    def test_create_archive_skips_hidden_by_default(self) -> None:
        self._create_structure()
        archive = create_archive([self.root / "docs"], output=self.root / "out.zip")

        with zipfile.ZipFile(archive) as zf:
            names = set(zf.namelist())

        self.assertIn("docs/notes.txt", names)
        self.assertNotIn("docs/.secret.txt", names)

    def test_copy_to_locations_creates_copies(self) -> None:
        (self.root / "sample.txt").write_text("data")
        archive = create_archive([self.root / "sample.txt"], output=self.root / "archive.zip")
        cloud_a = self.root / "cloud-a"
        cloud_b = self.root / "cloud-b"

        results = copy_to_locations(archive, [cloud_a, cloud_b])

        self.assertEqual({cloud_a.resolve(), cloud_b.resolve()}, {directory for directory, _ in results})
        self.assertTrue((cloud_a / "archive.zip").exists())
        self.assertTrue((cloud_b / "archive.zip").exists())


class GuiTests(unittest.TestCase):
    def test_main_exits_cleanly_when_display_unavailable(self) -> None:
        with mock.patch("tkinter.Tk", side_effect=tk.TclError("no display")):
            with self.assertRaises(SystemExit) as cm:
                gui.main()

        self.assertIn("Ensure a graphical display is available", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
