"""Minimal web server exposing FileZipper functionality."""

from __future__ import annotations

import atexit
import html
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import unquote_plus
from wsgiref.simple_server import make_server
from wsgiref.util import setup_testing_defaults

from .zipper import copy_to_locations, create_archive


@dataclass
class ArchiveResult:
    """Holds information about a created archive."""

    archive_path: Path
    copies: List[Path]


class FileZipperWebApp:
    """WSGI application providing a web form for archive creation."""

    def __init__(self) -> None:
        self._storage_dir = Path(tempfile.mkdtemp(prefix="filezipper-web-"))
        self._results: Dict[str, ArchiveResult] = {}
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        if self._storage_dir.exists():
            for item in sorted(self._storage_dir.glob("*")):
                try:
                    item.unlink()
                except OSError:
                    pass
            try:
                self._storage_dir.rmdir()
            except OSError:
                pass

    # ------------------------------------------------------------------
    # WSGI entry point
    # ------------------------------------------------------------------
    def __call__(self, environ, start_response):  # type: ignore[override]
        setup_testing_defaults(environ)
        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "GET").upper()

        if path == "/" and method == "GET":
            return self._respond(start_response, self._render_form())

        if path == "/" and method == "POST":
            length = int(environ.get("CONTENT_LENGTH") or 0)
            body = environ["wsgi.input"].read(length)
            return self._handle_submit(body, start_response)

        if path.startswith("/download/") and method == "GET":
            token = path.split("/", 2)[-1]
            return self._handle_download(token, start_response)

        return self._respond(start_response, self._render_form(message="Not found."), status="404 Not Found")

    # ------------------------------------------------------------------
    def _handle_submit(self, body: bytes, start_response):
        parsed = self._parse_form(body)

        sources = self._lines(parsed.get("sources", ""))
        if not sources:
            return self._respond(start_response, self._render_form(message="Please provide at least one source path."))

        destinations = self._lines(parsed.get("destinations", ""))
        output_text = parsed.get("output") or None
        include_hidden = parsed.get("include_hidden") == "on"

        try:
            if output_text:
                archive_path = create_archive(sources, output=output_text, include_hidden=include_hidden)
            else:
                archive_path = create_archive(sources, output=self._storage_dir, include_hidden=include_hidden)
        except Exception as exc:  # pragma: no cover - surface errors to UI
            message = f"Error: {html.escape(str(exc))}"
            return self._respond(start_response, self._render_form(message=message, form_data=parsed))

        copies: List[Path] = []
        try:
            if destinations:
                copies = [path for _, path in copy_to_locations(archive_path, destinations)]
        except Exception as exc:  # pragma: no cover - surface errors to UI
            message = f"Archive created at {html.escape(str(archive_path))}, but copying failed: {html.escape(str(exc))}"
            return self._respond(
                start_response,
                self._render_form(message=message, form_data=parsed, archive=archive_path, copies=copies),
            )

        token = uuid.uuid4().hex
        self._results[token] = ArchiveResult(archive_path=archive_path, copies=copies)

        return self._respond(
            start_response,
            self._render_form(
                message="Archive created successfully!",
                form_data={},
                archive=archive_path,
                copies=copies,
                token=token,
            ),
        )

    # ------------------------------------------------------------------
    def _handle_download(self, token: str, start_response):
        info = self._results.get(token)
        if not info:
            return self._respond(start_response, self._render_form(message="Archive is no longer available."))

        try:
            data = info.archive_path.read_bytes()
        except OSError:
            return self._respond(start_response, self._render_form(message="Unable to read archive."))

        headers = [
            ("Content-Type", "application/zip"),
            ("Content-Length", str(len(data))),
            ("Content-Disposition", f"attachment; filename={info.archive_path.name}"),
        ]
        start_response("200 OK", headers)
        return [data]

    # ------------------------------------------------------------------
    def _parse_form(self, body: bytes) -> Dict[str, str]:
        text = body.decode("utf-8")
        pairs = text.split("&") if text else []
        result: Dict[str, str] = {}
        for pair in pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
            else:
                key, value = pair, ""
            result[self._decode(key)] = self._decode(value)
        return result

    def _decode(self, value: str) -> str:
        return unquote_plus(value)

    def _lines(self, value: str) -> List[str]:
        return [line.strip() for line in value.splitlines() if line.strip()]

    def _render_form(
        self,
        message: str | None = None,
        form_data: Dict[str, str] | None = None,
        archive: Path | None = None,
        copies: Iterable[Path] = (),
        token: str | None = None,
    ) -> str:
        form_data = form_data or {}
        sources_value = html.escape(form_data.get("sources", ""))
        destinations_value = html.escape(form_data.get("destinations", ""))
        output_value = html.escape(form_data.get("output", ""))
        include_hidden_checked = "checked" if form_data.get("include_hidden") == "on" else ""

        copies_list = "".join(f"<li>{html.escape(str(path))}</li>" for path in copies)
        copies_section = f"<h3>Copies</h3><ul>{copies_list}</ul>" if copies_list else ""

        archive_section = ""
        if archive is not None:
            archive_section = f"<p>Archive location: {html.escape(str(archive))}</p>"
            if token:
                archive_section += f'<p><a href="/download/{token}">Download archive</a></p>'

        message_block = f"<div class='message'>{html.escape(message)}</div>" if message else ""

        return f"""
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>FileZipper Web</title>
    <style>
      body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8f9fa; }}
      form {{ background: #fff; padding: 1.5rem; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
      .field {{ margin-bottom: 1rem; }}
      label {{ display: block; font-weight: 600; margin-bottom: 0.4rem; }}
      textarea, input[type=text] {{ width: 100%; padding: 0.5rem; border: 1px solid #ced4da; border-radius: 0.25rem; }}
      button {{ background: #0d6efd; color: white; padding: 0.6rem 1.2rem; border: none; border-radius: 0.25rem; cursor: pointer; }}
      button:hover {{ background: #0b5ed7; }}
      .message {{ margin-bottom: 1rem; padding: 0.75rem; background: #e7f5ff; border: 1px solid #b6d4fe; border-radius: 0.25rem; }}
      .note {{ font-size: 0.9rem; color: #6c757d; }}
    </style>
  </head>
  <body>
    <h1>FileZipper Web</h1>
    {message_block}
    <form method="post">
      <div class="field">
        <label for="sources">Source paths</label>
        <textarea id="sources" name="sources" required placeholder="One path per line">{sources_value}</textarea>
        <p class="note">Provide files or directories available on the server.</p>
      </div>
      <div class="field">
        <label for="output">Output path (optional)</label>
        <input id="output" name="output" type="text" value="{output_value}" placeholder="Leave empty to use the app storage directory">
      </div>
      <div class="field">
        <label for="destinations">Copy destinations (optional)</label>
        <textarea id="destinations" name="destinations" placeholder="One path per line">{destinations_value}</textarea>
      </div>
      <div class="field">
        <label><input type="checkbox" name="include_hidden" {include_hidden_checked}> Include hidden files</label>
      </div>
      <button type="submit">Create archive</button>
    </form>
    <div>
      {archive_section}
      {copies_section}
    </div>
  </body>
</html>
"""

    def _respond(self, start_response, content: str, status: str = "200 OK"):
        data = content.encode("utf-8")
        headers = [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(data)))]
        start_response(status, headers)
        return [data]


def create_app() -> FileZipperWebApp:
    """Return a configured web application instance."""

    return FileZipperWebApp()


def main() -> None:
    """Launch the development server."""

    app = create_app()
    with make_server("0.0.0.0", 5000, app) as httpd:
        print("Serving on http://0.0.0.0:5000")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:  # pragma: no cover - manual exit
            print("\nShutting down server")


__all__ = ["create_app", "main", "FileZipperWebApp"]


if __name__ == "__main__":  # pragma: no cover - manual execution
    main()
