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
    unittest.main()
