from pathlib import Path

from remove_empty_folder.scanner import is_ignorable, remove, scan


def touch(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")


def names(cands, root):
    return {str(c.path.relative_to(root)) for c in cands}


def test_is_ignorable():
    assert is_ignorable(".DS_Store")
    assert is_ignorable("THUMBS.DB")
    assert is_ignorable("debug.log")
    assert is_ignorable("._photo.jpg")
    assert not is_ignorable("photo.jpg")


def test_scan_finds_topmost_empty(tmp_path):
    (tmp_path / "empty").mkdir()
    (tmp_path / "nested/a/b").mkdir(parents=True)
    touch(tmp_path / "junk/.DS_Store")
    touch(tmp_path / "junk/sub/x.tmp")
    touch(tmp_path / "keep/real.txt")
    (tmp_path / "keep/emptychild").mkdir()

    found = scan(tmp_path)
    assert names(found, tmp_path) == {"empty", "nested", "junk", "keep/emptychild"}
    junk = next(c for c in found if c.path.name == "junk")
    assert len(junk.ignored_files) == 2 and junk.subdirs == 1


def test_root_never_candidate(tmp_path):
    assert scan(tmp_path) == []


def test_symlink_keeps_folder(tmp_path):
    touch(tmp_path / "target.txt")
    (tmp_path / "link_dir").mkdir()
    (tmp_path / "link_dir/l").symlink_to(tmp_path / "target.txt")
    assert scan(tmp_path) == []


def test_remove_rechecks(tmp_path):
    touch(tmp_path / "d/.DS_Store")
    [c] = scan(tmp_path)
    touch(tmp_path / "d/new.txt")  # content appeared after scan
    assert remove(c.path) is False and c.path.exists()
    (tmp_path / "d/new.txt").unlink()
    assert remove(c.path) is True and not c.path.exists()


def test_scan_reports_progress(tmp_path):
    (tmp_path / "a" / "x").mkdir(parents=True)
    (tmp_path / "b").mkdir()
    calls = []
    scan(tmp_path, progress=lambda p, d, t, s: calls.append((p.name, d, t, s)))
    assert calls[-1][1:] == (2, 2, 4)  # 2/2 top-level done, 4 dirs seen incl. root


def test_scan_non_recursive_only_reports_direct_children(tmp_path):
    (tmp_path / "empty" / "nested").mkdir(parents=True)  # whole subtree empty
    touch(tmp_path / "full" / "real.txt")
    (tmp_path / "full" / "deep_empty").mkdir()
    names = lambda r: [c.path.name for c in scan(tmp_path, recursive=r)]
    assert names(True) == ["empty", "deep_empty"]
    assert names(False) == ["empty"]
