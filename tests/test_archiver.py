from datetime import date
import archiver
import manifest
import backlog_archive


def _mk(out, rel, body="x"):
    f = out / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)
    return f


def test_moves_only_manifested_and_old(tmp_path):
    out = tmp_path / "posts"
    _mk(out, "crypto/2026-01-01-old-done.md")
    _mk(out, "crypto/2026-01-02-old-undone.md")
    _mk(out, "crypto/2026-06-08-new-done.md")
    m = out / "synthesized.txt"
    manifest.append(m, ["crypto/2026-01-01-old-done.md", "crypto/2026-06-08-new-done.md"])
    moved = archiver.run(out, m, today=date(2026, 6, 8), keep_days=14)
    assert moved == ["crypto/2026-01-01-old-done.md"]
    assert (out / "crypto/archive/2026-01-01-old-done.md").exists()
    assert (out / "crypto/2026-01-02-old-undone.md").exists()
    assert (out / "crypto/2026-06-08-new-done.md").exists()


def test_no_clobber_keeps_existing_archive(tmp_path):
    """A same-named new article must not silently overwrite an archived copy."""
    out = tmp_path / "posts"
    archived = _mk(out, "crypto/archive/2026-01-01-a.md", body="OLD ARCHIVED")
    new = _mk(out, "crypto/2026-01-01-a.md", body="NEW")
    m = out / "synthesized.txt"
    manifest.append(m, ["crypto/2026-01-01-a.md"])
    moved = archiver.run(out, m, today=date(2026, 6, 1), keep_days=14)
    assert moved == []  # collision -> not moved
    assert archived.read_text() == "OLD ARCHIVED"  # archive untouched
    assert new.read_text() == "NEW"  # root file left in place


def test_excludes_synthesis_and_nodate_and_baddate(tmp_path):
    out = tmp_path / "posts"
    _mk(out, "crypto/SYNTHESIS-archive-pre-2026-05-24.md")
    _mk(out, "crypto/no-date.md")
    _mk(out, "crypto/2026-13-99-baddate.md")
    m = out / "synthesized.txt"
    manifest.append(m, [
        "crypto/SYNTHESIS-archive-pre-2026-05-24.md",
        "crypto/no-date.md",
        "crypto/2026-13-99-baddate.md",
    ])
    moved = archiver.run(out, m, today=date(2026, 6, 8), keep_days=14)
    assert moved == []


def test_idempotent(tmp_path):
    out = tmp_path / "posts"
    _mk(out, "crypto/2026-01-01-a.md")
    m = out / "synthesized.txt"
    manifest.append(m, ["crypto/2026-01-01-a.md"])
    archiver.run(out, m, today=date(2026, 6, 8), keep_days=14)
    moved2 = archiver.run(out, m, today=date(2026, 6, 8), keep_days=14)
    assert moved2 == []


def test_gap_detection(tmp_path):
    syn = tmp_path / "synthesis"
    syn.mkdir()
    for d in ["2026-04-13", "2026-04-15", "2026-05-19", "2026-05-23"]:
        (syn / f"{d}-synthesis.md").write_text("x")
    gaps = backlog_archive.uncovered_dates(
        syn, lookback=2, start=date(2026, 4, 13), end=date(2026, 5, 23))
    assert date(2026, 5, 20) in gaps      # 5/19 covers 5/17-19, 5/23 covers 5/21-23 → 5/20 gap
    assert date(2026, 4, 14) not in gaps  # covered by 4/15 digest
