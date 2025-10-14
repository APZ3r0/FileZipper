from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlencode

from filezipper.web import create_app


def make_request(app, method: str, path: str, body: bytes = b"", headers: Dict[str, str] | None = None):
    status: List[str] = []
    response_headers: List[Tuple[str, str]] = []

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "wsgi.input": io.BytesIO(body),
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": "application/x-www-form-urlencoded",
    }
    if headers:
        environ.update(headers)

    def start_response(status_line, hdrs):
        status.append(status_line)
        response_headers.extend(hdrs)

    result = app(environ, start_response)
    content = b"".join(result)
    return status[0], response_headers, content


class WebAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.app = create_app()

    def test_index_renders(self) -> None:
        status, headers, body = make_request(self.app, "GET", "/")
        self.assertEqual(status, "200 OK")
        self.assertIn(b"FileZipper Web", body)

    def test_create_archive_and_download(self) -> None:
        root = Path(self.temp_dir.name)
        source_dir = root / "data"
        source_dir.mkdir()
        (source_dir / "notes.txt").write_text("meeting notes")
        cloud_dir = root / "cloud"

        form = urlencode(
            {
                "sources": str(source_dir),
                "destinations": str(cloud_dir),
            }
        ).encode("utf-8")

        status, headers, body = make_request(self.app, "POST", "/", body=form)
        self.assertEqual(status, "200 OK")
        self.assertIn(b"Archive created successfully!", body)
        self.assertIn(b"Download archive", body)

        start = body.find(b"/download/")
        token = body[start + len("/download/") :].split(b"\"", 1)[0].decode("utf-8")

        status, headers, content = make_request(self.app, "GET", f"/download/{token}")
        self.assertEqual(status, "200 OK")
        header_dict = dict(headers)
        self.assertEqual(header_dict.get("Content-Type"), "application/zip")
        self.assertIn("filename=", header_dict.get("Content-Disposition", ""))

        archive_name = header_dict["Content-Disposition"].split("filename=")[-1]
        copied_archive = cloud_dir / archive_name
        self.assertTrue(copied_archive.exists())


if __name__ == "__main__":
    unittest.main()
