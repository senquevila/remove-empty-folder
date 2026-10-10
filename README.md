# remove-empty-folder

A terminal UI for finding and deleting folders that hold no real files.

Folders often look empty but still contain system leftovers like `.DS_Store`,
`Thumbs.db` or old `.tmp` files, so normal "delete empty folder" tools skip
them. This app treats those files as junk. It lists every folder that holds
nothing else, lets you check the ones to remove, and deletes them after you
confirm.

Built with Python and [Textual](https://textual.textualize.io/).

## Requirements

- Python 3.9 or newer
- macOS, Linux or Windows

## Install

```bash
cd remove-empty-folder
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

This installs the `remove-empty-folder` command into the virtual environment.

## Usage

```bash
remove-empty-folder                     # scan the current folder
remove-empty-folder ~/Downloads         # scan a specific folder
remove-empty-folder ~/Downloads --dry-run   # preview only, deletes nothing
python -m remove_empty_folder ~/Downloads   # same, without the command
```

When the app opens, it scans the folder right away. Every empty folder it finds
is listed and selected. Uncheck any you want to keep, then press `d`.

### Keys

| Key     | Action                                    |
|---------|-------------------------------------------|
| `s`     | Scan again (or press Enter in the path box) |
| `space` | Check or uncheck the highlighted folder   |
| `a`     | Select all                                |
| `n`     | Select none                               |
| `d`     | Delete the selected folders (asks first)  |
| `q`     | Quit                                      |

You can type a different path in the box at the top and press Enter to scan it.
The panel on the right lists the ignored files inside the highlighted folder,
which are deleted along with it.

## What counts as empty

A folder is empty when everything inside it is one of these:

- another empty folder, or
- a file whose name ends with an entry in `IGNORED_EXTENSIONS`, or starts with
  an entry in `IGNORED_PREFIXES`.

Example, scanning `projects/`:

```
projects/
├── old-build/          ← listed (only .DS_Store and an empty subfolder)
│   ├── .DS_Store
│   └── cache/
├── scratch/            ← listed (only a .tmp file)
│   └── session.tmp
└── website/            ← kept (has a real file)
    ├── index.html
    └── assets/         ← listed (empty, even though its parent is kept)
```

When empty folders are nested, only the outermost one is listed, because
deleting it removes the rest.

## Configuration

Edit `src/remove_empty_folder/config.py`:

```python
IGNORED_EXTENSIONS = (
    ".DS_Store", "Thumbs.db", "desktop.ini", ".localized",
    ".tmp", ".temp", ".log", ".bak", ".swp", ".part", ".crdownload",
)

IGNORED_PREFIXES = ("._",)   # macOS AppleDouble files such as "._photo.jpg"
```

Matching ignores upper/lower case and checks the end of the file name, so you
can list either an extension (`.log`) or a full file name (`Thumbs.db`).

Note that `.log`, `.bak` and `.part` are on the list by default, so a folder
holding only a backup or a partly downloaded file will be offered for deletion.
Remove those entries if you want to keep such folders.

## Safety

- The folder you scan is never deleted, only folders inside it.
- Symbolic links are never followed. A folder that contains one is kept.
- Folders that can't be read are kept.
- Each folder is checked again right before it is deleted. If it gained a real
  file since the scan, it is skipped.
- Nothing is deleted without a confirmation dialog, and `--dry-run` deletes
  nothing at all.

Deleted folders do not go to the Trash. Use `--dry-run` first if you are unsure.

## Project layout

```
src/remove_empty_folder/
├── config.py     # IGNORED_EXTENSIONS and IGNORED_PREFIXES
├── scanner.py    # finding, re-checking and deleting empty folders
├── app.py        # the Textual interface
└── __main__.py   # command-line entry point
tests/
└── test_scanner.py
```

## Tests

```bash
pytest
```
