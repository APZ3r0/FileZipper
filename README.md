# FileZipper

FileZipper is a simple command line tool that bundles files and directories into ZIP
archives and optionally copies the resulting archive to one or more destinations
(e.g. a synced cloud storage folder).

## Installation

Clone this repository and install the project in editable mode:

```bash
pip install -e .
```

Alternatively, you can run the module directly without installing:

```bash
python -m filezipper.cli <sources>
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

## Development

Run the tests with:

```
python -m unittest tests.test_zipper
```
