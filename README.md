# FileZipper (no-nonsense edition)

Executives asked for something that “just zips the folder and gives me a copy.”
This version does exactly that with nothing but the Python standard library.
Double-click the launcher and a friendly window walks you through the three
steps. If your computer cannot show the window (for example on a server), the
tool automatically falls back to the plain-text helper.

## What it does
- asks for one file or folder
- builds a ZIP file in the same place (or a spot you choose)
- optionally drops one extra copy somewhere else (perfect for a synced cloud folder)

## Setup in plain English
1. **Install Python 3.9 or newer.** Grab it from [python.org](https://www.python.org/downloads/)
   and tick the “Add Python to PATH” box during install.
2. **Download this project.** Press the green *Code* button on GitHub and choose
   *Download ZIP*. Unzip it somewhere easy to find (Desktop is fine).
3. **Run the helper.**
   - Keep `run_filezipper.py` in the same folder as the `filezipper` directory.
   - Double-click `run_filezipper.py` and use the point-and-click window.
   - If a window cannot open, the launcher automatically switches to a simple
     text version and keeps the console visible so you can read the messages.

That’s it. The program will talk you through the rest in normal human language.

## Using the point-and-click window
1. Press **File…** or **Folder…** to choose what should be zipped.
2. (Optional) Use **Browse…** to choose where the ZIP should be saved (the file
   will be named after what you picked, e.g. `Project.zip`).
3. (Optional) Pick a spot for an extra copy.
4. Press **Start**.

You will see a confirmation message that lists exactly where the ZIP (and any
backup copy) ended up.

## Using the console helper
If you prefer typing paths, or you are on a system without a desktop, launch the
helper from a terminal with `python run_filezipper.py`. You will see three short
questions. Answer them just like before and the tool will report the final ZIP
location(s).

## Why this version is easy
- 100% standard library, so there is nothing extra to install.
- Point-and-click window for the C-suite, terminal fallback for everyone else.
- Works the same on Windows, macOS, or Linux.

## Developers / power users
Prefer the old-school terminal workflow? Install the project in editable mode
and use the entry point:

```bash
python -m pip install -e .
filezipper
```

Or import the helpers directly:

```python
from filezipper import create_zip, make_copy
```

Automated tests can be run with:

```bash
python -m unittest tests.test_zipper
```
