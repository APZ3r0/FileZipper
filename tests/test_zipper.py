from __future__ import annotations

import tempfile
import unittest
from unittest import mock
import zipfile
from pathlib import Path

from filezipper.zipper import create_zip, make_copy


class RunFileZipperTests(unittest.TestCase):
    def test_launch_falls_back_to_cli_when_gui_errors(self) -> None:
        import run_filezipper

        with mock.patch("run_filezipper._prepare_path"), mock.patch(
            "filezipper.simple_gui.launch", side_effect=RuntimeError("boom")
        ), mock.patch("run_filezipper.print"), mock.patch(
            "run_filezipper._run_cli", return_value=0
        ) as run_cli:
            exit_code = run_filezipper._launch()

        self.assertEqual(exit_code, 0)
        run_cli.assert_called_once()


class FileZipperTests(unittest.TestCase):
    def test_create_zip_from_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "hello.txt"
            source.write_text("hi", encoding="utf-8")

            archive = create_zip(source)

            self.assertTrue(archive.exists())
            with zipfile.ZipFile(archive) as zf:
                self.assertEqual(sorted(zf.namelist()), ["hello.txt"])
                self.assertEqual(zf.read("hello.txt").decode("utf-8"), "hi")

    def test_create_zip_to_custom_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "data.txt"
            source.write_text("payload", encoding="utf-8")
            custom_zip = tmp_path / "custom" / "bundle.zip"

            archive = create_zip(source, custom_zip)

            self.assertEqual(archive, custom_zip.resolve())
            with zipfile.ZipFile(archive) as zf:
                self.assertEqual(zf.namelist(), ["data.txt"])

    def test_create_zip_from_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            folder = tmp_path / "docs"
            folder.mkdir()
            (folder / "report.txt").write_text("quarterly", encoding="utf-8")
            (folder / ".hidden.txt").write_text("should be included", encoding="utf-8")

            archive = create_zip(folder)

            with zipfile.ZipFile(archive) as zf:
                names = sorted(zf.namelist())
                self.assertEqual(names, ["docs/.hidden.txt", "docs/report.txt"])

    def test_make_copy_to_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "demo.txt"
            source.write_text("ok", encoding="utf-8")
            archive = create_zip(source)

            destination = tmp_path / "copies"
            copy_path = make_copy(archive, destination)

            self.assertTrue(copy_path.exists())
            self.assertEqual(copy_path.parent, destination)
            with zipfile.ZipFile(copy_path) as zf:
                self.assertEqual(zf.namelist(), ["demo.txt"])

    def test_make_copy_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            source = tmp_path / "demo.txt"
            source.write_text("ok", encoding="utf-8")
            archive = create_zip(source)

            custom_file = tmp_path / "backup.zip"
            copy_path = make_copy(archive, custom_file)

            self.assertEqual(copy_path, custom_file.resolve())
            with zipfile.ZipFile(copy_path) as zf:
                self.assertEqual(zf.namelist(), ["demo.txt"])

    def test_missing_source_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "nope.txt"
            with self.assertRaises(FileNotFoundError):
                create_zip(missing)

    def test_missing_archive_for_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "no.zip"
            with self.assertRaises(FileNotFoundError):
                make_copy(missing, Path(tmp_dir))


if __name__ == "__main__":  # pragma: no cover
import zipfile
from pathlib import Path

import unittest
from unittest import mock

import tkinter as tk

from filezipper.zipper import copy_to_locations, create_archive
from filezipper import gui

from filezipper.zipper import copy_to_locations, create_archive


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
