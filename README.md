# FileZipper

FileZipper is a simple command line tool that bundles files and directories into ZIP
archives and optionally copies the resulting archive to one or more destinations
(e.g. a synced cloud storage folder). A desktop GUI is also provided for users who
prefer a point-and-click workflow.

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

## Development

Run the tests with:

```
python -m unittest tests.test_zipper
```
