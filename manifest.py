"""Manifest: tracks which articles have been synthesized (append-only),
plus the shared article-file conventions used by synthesizer / archiver / backlog."""
import re
from pathlib import Path
from datetime import date, datetime
from typing import Iterator

MANIFEST_NAME = "synthesized.txt"
RESERVED_DIRS = {"synthesis"}
SYNTHESIS_PREFIX = "SYNTHESIS-"
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def default_path(output_dir: Path) -> Path:
    return output_dir / MANIFEST_NAME


def parse_article_date(name: str):
    """Date from a `YYYY-MM-DD-...md` filename, or None (incl. bad dates like 2026-13-99)."""
    m = DATE_RE.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def iter_dated_articles(output_dir: Path) -> Iterator[Path]:
    """Yield every dated article .md in topic folders. Single source of truth for
    'what counts as an archivable article file': skips RESERVED_DIRS, SYNTHESIS-* files,
    no-date / bad-date files, and (via non-recursive glob) each topic's archive/ subdir."""
    for topic_dir in sorted(output_dir.iterdir()):
        if not topic_dir.is_dir() or topic_dir.name in RESERVED_DIRS:
            continue
        for md_file in sorted(topic_dir.glob("*.md")):
            name = md_file.name
            if name.startswith(SYNTHESIS_PREFIX):
                continue
            if parse_article_date(name) is None:
                continue
            yield md_file


def load(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()
    return {
        ln.strip()
        for ln in manifest_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    }


def append(manifest_path: Path, rel_paths: list[str]) -> None:
    """Mark paths synthesized. Callers must batch (reads the file once per call)."""
    existing = load(manifest_path)
    new = [p for p in rel_paths if p not in existing]
    if not new:
        return
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as fh:
        for p in new:
            fh.write(p + "\n")


def rel_path(md_file: Path, output_dir: Path) -> str:
    return str(md_file.relative_to(output_dir))
