# FileZipper (no-nonsense edition)

Executives asked for something that “just zips the folder and gives me a copy.”
This version does exactly that with nothing but the Python standard library.
No web server, no GUI toolkits, no frameworks.

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
   - Windows: double-click `run_filezipper.py`.
   - macOS/Linux: open a terminal in the folder and run `python run_filezipper.py`.

That’s it. The program will talk you through the rest in normal human language.

## Using the console helper
When it starts you’ll see three short questions:
1. *“What file or folder should we zip?”* — type a path or drag a folder into the
   window.
2. *“Where should the finished ZIP live?”* — press Enter to use the same folder,
   or paste another location.
3. *“Do you want to drop a copy somewhere else too?”* — say `y` if you want a
   second copy (for example, inside your cloud-sync folder) and paste the path.

The program repeats the final location(s) so you know exactly where everything
ended up. Nothing else to learn.

## Why this version is easy
- 100% standard library, so there is nothing extra to install.
- All instructions are printed on screen while you use it.
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
