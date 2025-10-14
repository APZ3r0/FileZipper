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
# FileZipper

FileZipper is a simple tool that bundles files and directories into ZIP archives and
optionally copies the resulting archive to one or more destinations (e.g. a synced
cloud storage folder). A command line interface, desktop GUI, and web application
are available so you can pick the workflow that fits best.

## Quick start for beginners

If you have never used Python before, follow these steps to get the app running:

1. **Install Python 3.10 or newer.** Download the Windows or macOS installer from
   [python.org/downloads](https://www.python.org/downloads/) and run it. Make sure
   you check the option that says “Add Python to PATH” during installation.
2. **Download this project.** Click the green “Code” button on the repository
   page and choose “Download ZIP”. Unzip the contents to a folder that is easy to
   find, such as your Desktop.
3. **Open a terminal in the project folder.**
   - On Windows press `Win + R`, type `cmd`, and press Enter. In the Command
     Prompt run:
     ```
     cd %USERPROFILE%\Desktop\FileZipper-main
     ```
   - On macOS open the Terminal app and run:
     ```
     cd ~/Desktop/FileZipper-main
     ```
4. **Create an isolated Python environment (recommended but optional):**
   ```
   python -m venv .venv
   ```
   Activate it with `.\.venv\Scripts\activate` on Windows or `source .venv/bin/activate`
   on macOS/Linux.
5. **Install the program and its dependencies:**
   ```
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```

Once the installation finishes you can pick whichever interface you prefer.

### Command line (terminal) version

Run the tool directly from your terminal:

```
python -m filezipper.cli <sources>
```

Replace `<sources>` with one or more file or folder paths.

### Desktop app

Start the graphical interface:

```
python -m filezipper.gui
```

### Web app

Start the local web server:

```
python -m filezipper.web
```

After the server prints `Serving on http://localhost:5000`, open a browser to
that address.

## Installation

Clone this repository and install the project in editable mode:

```bash
pip install -e .
```

Alternatively, you can run the module directly without installing:

```bash
python -m filezipper.cli <sources>
```

To launch the graphical interface without installing, use:

```bash
python -m filezipper.gui
```

To start the web application without installing, use:

```bash
python -m filezipper.web
```

## Usage

```
python -m filezipper.cli <sources> [options]
```

| Option | Description |
| ------ | ----------- |
| `-o, --output` | Output file path or directory. If a directory is supplied a timestamped archive name is generated automatically. |
| `-c, --cloud-destination` | Directory or file path where the archive should be copied. Supply the flag multiple times to copy the archive to more than one location. |
| `--include-hidden` | Include hidden files and directories when walking source directories. |

### Examples

Create an archive from two folders and store it in the current directory:

```
python -m filezipper.cli ./documents ./photos
```

Create an archive that includes hidden files and copy it to a Dropbox folder:

```
python -m filezipper.cli ./project --include-hidden \
  --cloud-destination "~/Dropbox/backups"
```

Specify an explicit output path and create multiple copies:

```
python -m filezipper.cli ./data -o ./backups/data.zip \
  --cloud-destination ./drive --cloud-destination ./offsite
```

## Graphical interface

After installing the package a `filezipper-gui` command becomes available. Launching
it opens a Tkinter-based desktop application that exposes the same functionality as
the CLI:

```
```bash
filezipper-gui
```

Within the GUI you can:

- Add files or folders to the archive source list.
- Choose an output file name or target directory.
- Select optional copy destinations (such as synced cloud folders).
- Decide whether hidden files should be included.
- View a running log of archive creation and copy operations.

When the archive is created, any configured destinations receive a copy of the
resulting ZIP file automatically.

## Web application

The `filezipper-web` entry point launches a lightweight HTTP server that runs
locally. After starting the server, open a browser to `http://localhost:5000` to
access the interface.

Within the web app you can:

- List the files or directories that should be included in the archive (one path
  per line).
- Optionally provide a server-side output path where the archive should be stored.
- Supply one or more copy destinations (one per line). Each destination can be a
  directory or file path and receives a copy of the archive.
- Download the generated archive directly from the browser.

## Development

Run the tests with:

```
python -m unittest discover -s tests -p "test_*.py"
python -m unittest tests.test_zipper
```
