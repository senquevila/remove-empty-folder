"""Configuration constants."""

# Files whose names end with one of these extensions do NOT count as content.
# A directory that only contains files like these (and/or empty subdirectories)
# is considered empty and can be removed. Matching is case-insensitive and is
# done against the end of the file name, so full names such as ".DS_Store" or
# "Thumbs.db" work too.
IGNORED_EXTENSIONS: tuple[str, ...] = (
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    ".localized",
    ".tmp",
    ".temp",
    ".log",
    ".bak",
    ".swp",
    ".part",
    ".crdownload",
)

# File name prefixes that are also ignored (e.g. macOS AppleDouble "._foo").
IGNORED_PREFIXES: tuple[str, ...] = ("._",)
