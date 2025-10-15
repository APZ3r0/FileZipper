"""Launch the FileZipper helper while keeping the console window open."""

from __future__ import annotations

from pathlib import Path
import sys


def _pause() -> None:
    """Wait for the user so the console window stays visible."""

    try:
        input("\nPress Enter to close this window.")
    except EOFError:
        # When stdin is closed (for example when launched from certain shells)
        # we simply skip the pause.
        pass


def _prepare_path() -> None:
    """Ensure the local copy of the package is importable when double-clicked."""

    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))


def _run_cli() -> int:
    """Launch the text-based helper and keep the console visible."""
def _launch() -> int:
    _prepare_path()

    try:
        from filezipper.cli import main as cli_main
    except ModuleNotFoundError:
        print(
            "I couldn't start FileZipper because its files are missing."
            "\nMake sure run_filezipper.py stays in the same folder as the"
            "\n'filezipper' directory that ships with it."
        )
        _pause()
        return 1

    try:
        exit_code = cli_main()
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"FileZipper ran into a problem: {exc}")
        _pause()
        return 1

    _pause()
    return exit_code


def _launch() -> int:
    _prepare_path()

    try:
        from filezipper.simple_gui import launch as launch_gui
    except ModuleNotFoundError:
        launch_gui = None

    if launch_gui is not None:
        try:
            return launch_gui()
        except Exception as exc:  # pragma: no cover - defensive guard
            print("I couldn't open the easy window, so I'll switch to the text helper instead.")
            print(f"Reason: {exc}")

    return _run_cli()


if __name__ == "__main__":
    raise SystemExit(_launch())
if __name__ == "__main__":
    raise SystemExit(_launch())
"""Launch the FileZipper helper in a way that keeps the window open when run directly."""

from __future__ import annotations

from filezipper.cli import main

if __name__ == "__main__":
    exit_code = main()
    try:
        input("\nPress Enter to close this window.")
    except EOFError:
        pass
    raise SystemExit(exit_code)
