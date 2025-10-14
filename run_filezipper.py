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
