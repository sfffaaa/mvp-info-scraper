from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from models import Article
from synthesizer import format_synthesis_email


def test_format_synthesis_email_contains_key_sections():
    html = format_synthesis_email(
        report_text="## Key Themes\n- AI agents are rising\n\n## Actionable\n- Try X",
        article_count=12,
        date_str="2026-04-13",
    )
    assert "Key Themes" in html
    assert "Actionable" in html
    assert "12" in html
    assert "2026-04-13" in html


# --- archive mechanism: manifest-based loading + hub protection ---
import manifest as _manifest


def _mk_art(out, rel, body="# Title\nbody"):
    f = out / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    return f


def test_load_unsynthesized_excludes_manifest(tmp_path):
    import synthesizer
    out = tmp_path / "posts"
    _mk_art(out, "crypto/2026-06-01-a.md")
    _mk_art(out, "crypto/2026-06-02-b.md")
    m = out / "synthesized.txt"
    _manifest.append(m, ["crypto/2026-06-01-a.md"])
    arts = synthesizer.load_unsynthesized_articles(out, m)
    assert {a["rel"] for a in arts} == {"crypto/2026-06-02-b.md"}


def test_load_unsynthesized_excludes_synthesis_archive_nodate(tmp_path):
    import synthesizer
    out = tmp_path / "posts"
    _mk_art(out, "crypto/2026-06-01-a.md")
    _mk_art(out, "crypto/SYNTHESIS-archive-pre-2026-05-24.md")
    _mk_art(out, "crypto/archive/2026-04-01-old.md")
    _mk_art(out, "crypto/no-date-file.md")
    arts = synthesizer.load_unsynthesized_articles(out, out / "synthesized.txt")
    assert {a["rel"] for a in arts} == {"crypto/2026-06-01-a.md"}


def test_dryrun_report_still_has_four_sections(monkeypatch):
    import synthesizer
    monkeypatch.setattr(synthesizer, "_run_claude",
        lambda p, timeout=300: "## 主要主題\nx\n## 重要洞見\ny\n## 可行動項目\nz\n## 值得關注的信號\nw")
    rep = synthesizer.synthesize_with_claude(
        [{"title": "t", "topic": "crypto", "date": "2026-06-01", "content": "c", "rel": "crypto/x.md"}],
        "prefs", "")
    assert all(s in rep for s in synthesizer.REQUIRED_SECTIONS)


def test_chunk_failure_raises_not_silent_skip(monkeypatch):
    """Invariant: a failed chunk must raise so main() won't mark articles synthesized."""
    import synthesizer

    def boom(chunk):
        raise RuntimeError("claude timeout")

    monkeypatch.setattr(synthesizer, "_summarize_chunk", boom)
    arts = [{"title": "t", "topic": "crypto", "date": "2026-06-01",
             "content": "c", "rel": f"crypto/{i}.md"} for i in range(3)]
    import pytest
    with pytest.raises(RuntimeError):
        synthesizer.synthesize_with_claude(arts, "prefs", "")
