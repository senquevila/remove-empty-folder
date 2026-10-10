"""Textual TUI for removing empty directories."""

from __future__ import annotations

import time
from pathlib import Path

from rich.markup import escape
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, SelectionList, Static
from textual.widgets.selection_list import Selection

from .config import IGNORED_EXTENSIONS
from .scanner import Candidate, remove, scan


class ConfirmScreen(ModalScreen[bool]):
    """Yes/No confirmation dialog."""

    BINDINGS = [("y", "answer(True)", "Yes"), ("n,escape", "answer(False)", "No")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield Label(self.message, id="question")
            yield Button("Delete", variant="error", id="yes")
            yield Button("Cancel", variant="primary", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")

    def action_answer(self, value: bool) -> None:
        self.dismiss(value)


class RemoveEmptyFolderApp(App):
    TITLE = "Remove Empty Folders"
    CSS = """
    #top { height: auto; padding: 0 1; }
    #path { width: 1fr; }
    #summary { padding: 0 1; color: $text-muted; height: auto; }
    #main { height: 1fr; }
    #candidates { width: 2fr; border: round $primary; }
    #details { width: 1fr; border: round $secondary; padding: 0 1; overflow-y: auto; }
    ConfirmScreen { align: center middle; }
    #dialog {
        grid-size: 2; grid-gutter: 1 2; grid-rows: 1fr 3;
        padding: 0 1; width: 64; height: 12;
        border: thick $error 80%; background: $surface;
    }
    #question { column-span: 2; height: 1fr; width: 1fr; content-align: center middle; }
    #dialog Button { width: 100%; }
    """
    BINDINGS = [
        Binding("s", "scan", "Scan"),
        Binding("a", "select_all", "Select all"),
        Binding("n", "select_none", "Select none"),
        Binding("d", "delete", "Delete selected"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, root: str | Path = ".", dry_run: bool = False) -> None:
        super().__init__()
        self.root = Path(root).expanduser().resolve()
        self.dry_run = dry_run
        self.candidates: list[Candidate] = []
        if dry_run:
            self.sub_title = "DRY RUN — nothing will be deleted"

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top"):
            yield Input(str(self.root), placeholder="Directory to scan", id="path")
            yield Button("Scan", variant="primary", id="scan")
        yield Static(id="summary")
        with Horizontal(id="main"):
            yield SelectionList[int](id="candidates")
            with Vertical(id="details"):
                yield Static(id="detail-text")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#candidates").border_title = "Empty folders (space to toggle)"
        self.query_one("#details").border_title = "Details"
        self.query_one("#detail-text", Static).update(
            "Ignored extensions:\n" + "\n".join(f"  {e}" for e in IGNORED_EXTENSIONS)
        )
        self.action_scan()

    # ---- scanning -------------------------------------------------------
    @on(Button.Pressed, "#scan")
    @on(Input.Submitted, "#path")
    def action_scan(self) -> None:
        self.root = Path(self.query_one("#path", Input).value).expanduser().resolve()
        self.query_one("#summary", Static).update(f"Scanning {self.root} …")
        self.query_one("#candidates", SelectionList).clear_options()
        self.run_scan(self.root)

    @work(thread=True, exclusive=True)
    def run_scan(self, root: Path) -> None:
        last = 0.0

        def progress(path: Path, done: int, total: int, seen: int) -> None:
            nonlocal last
            now = time.monotonic()
            if now - last < 0.05:  # ponytail: throttle UI updates to ~20/s
                return
            last = now
            self.call_from_thread(self._set_summary, self._progress_line(path, done, total, seen))

        try:
            result = scan(root, progress=progress)
        except (OSError, NotADirectoryError) as exc:
            self.call_from_thread(self._set_summary, f"[red]Error:[/] {exc}")
            return
        self.call_from_thread(self._show_results, result)

    def _progress_line(self, path: Path, done: int, total: int, seen: int) -> str:
        width = 20
        filled = width * done // total if total else 0
        bar = "█" * filled + "░" * (width - filled)
        try:
            rel = path.relative_to(self.root)
        except ValueError:
            rel = path
        rel = str(rel)
        if len(rel) > 60:  # keep it on one line
            rel = "…" + rel[-59:]
        return f"Scanning [{bar}] {done}/{total} · {seen} folders · [dim]{escape(rel)}[/]"

    def _set_summary(self, text: str) -> None:
        self.query_one("#summary", Static).update(text)

    def _show_results(self, candidates: list[Candidate]) -> None:
        self.candidates = candidates
        sl = self.query_one("#candidates", SelectionList)
        sl.clear_options()
        sl.add_options(
            Selection(self._label(c), i, True) for i, c in enumerate(candidates)
        )
        if candidates:
            self._set_summary(
                f"Found [b]{len(candidates)}[/] removable folder(s) in {self.root}"
            )
            sl.focus()
        else:
            self._set_summary(f"No empty folders found in {self.root} 🎉")

    def _label(self, c: Candidate) -> str:
        try:
            rel = c.path.relative_to(self.root)
        except ValueError:
            rel = c.path
        extra = []
        if c.ignored_files:
            extra.append(f"{len(c.ignored_files)} ignored file(s)")
        if c.subdirs:
            extra.append(f"{c.subdirs} subdir(s)")
        return f"{rel}/" + (f"  [dim]({', '.join(extra)})[/]" if extra else "")

    @on(SelectionList.SelectionHighlighted)
    def show_details(self, event: SelectionList.SelectionHighlighted) -> None:
        c = self.candidates[event.selection.value]
        lines = [f"[b]{c.path}[/]", ""]
        if c.ignored_files:
            lines.append("Ignored files that will be deleted:")
            lines += [f"  • {f.relative_to(c.path)}" for f in c.ignored_files]
        else:
            lines.append("No files inside.")
        if c.subdirs:
            lines += ["", f"Contains {c.subdirs} empty subdirectory(ies)."]
        self.query_one("#detail-text", Static).update("\n".join(lines))

    # ---- selection ------------------------------------------------------
    def action_select_all(self) -> None:
        self.query_one("#candidates", SelectionList).select_all()

    def action_select_none(self) -> None:
        self.query_one("#candidates", SelectionList).deselect_all()

    # ---- deletion -------------------------------------------------------
    def action_delete(self) -> None:
        selected = self.query_one("#candidates", SelectionList).selected
        if not selected:
            self.notify("Nothing selected", severity="warning")
            return
        verb = "Simulate deleting" if self.dry_run else "Permanently delete"

        def handle(confirmed: bool | None) -> None:
            if confirmed:
                self._delete([self.candidates[i] for i in selected])

        self.push_screen(ConfirmScreen(f"{verb} {len(selected)} folder(s)?"), handle)

    def _delete(self, targets: list[Candidate]) -> None:
        deleted, skipped = 0, 0
        for c in targets:
            if self.dry_run:
                deleted += 1
                continue
            try:
                if remove(c.path):
                    deleted += 1
                else:
                    skipped += 1  # contents changed since scan
            except OSError as exc:
                skipped += 1
                self.notify(f"{c.path}: {exc}", severity="error")
        prefix = "[dry run] Would delete" if self.dry_run else "Deleted"
        msg = f"{prefix} {deleted} folder(s)"
        if skipped:
            msg += f", skipped {skipped} (no longer empty or error)"
        self.notify(msg)
        if not self.dry_run:
            self.action_scan()
