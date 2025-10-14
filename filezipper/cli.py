"""Ultra-simple console helper for creating ZIP files."""

from __future__ import annotations

from pathlib import Path

from .zipper import create_zip, make_copy


def _ask(prompt: str) -> str:
    """Read a line of input, returning an empty string when stdin closes."""

    try:
        return input(prompt)
    except EOFError:
        return ""


def main() -> int:
    print("FileZipper: the simple ZIP helper")
    print("---------------------------------")

    source_text = _ask("What file or folder should we zip? ").strip()
    if not source_text:
        print("You need to type the name of a file or folder.")
        return 1

    output_text = _ask(
        "Where should the finished ZIP live? (press Enter to put it next to the original) "
    ).strip()
    output_location: Path | None = Path(output_text) if output_text else None

    try:
        archive_path = create_zip(Path(source_text), output_location)
    except FileNotFoundError:
        print("I could not find that file or folder. Please double-check the spelling and try again.")
        return 1
    except Exception as exc:  # pragma: no cover - defensive guard
        print(f"Something went wrong while building the ZIP: {exc}")
        return 1

    print(f"All set! Your ZIP file lives at: {archive_path}")

    extra_copy = _ask("Do you want to drop a copy somewhere else too? (y/n) ").strip().lower()
    if extra_copy.startswith("y"):
        copy_target = _ask("Where should we drop the extra copy? ").strip()
        if copy_target:
            try:
                copied_path = make_copy(archive_path, Path(copy_target))
            except Exception as exc:  # pragma: no cover - defensive guard
                print(f"I couldn't copy the file: {exc}")
                return 1
            print(f"Done! Extra copy saved at: {copied_path}")
        else:
            print("No location provided, skipping the extra copy.")

    print("All done. Close this window or press Ctrl+C to exit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
