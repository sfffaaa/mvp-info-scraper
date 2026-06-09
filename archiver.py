"""Archiver: move synthesized + older-than-keep_days articles into <folder>/archive/."""
import re
import shutil
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

import manifest as manifest_mod

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def _parse_date(name: str):
    m = DATE_RE.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None  # bad date like 2026-13-99 → treat as no-date


def run(output_dir: Path, manifest_path: Path, today: date,
        keep_days: int = 14, dry_run: bool = False) -> list[str]:
    done = manifest_mod.load(manifest_path)
    cutoff = today - timedelta(days=keep_days)
    moved = []
    for topic_dir in sorted(output_dir.iterdir()):
        if not topic_dir.is_dir() or topic_dir.name in ("synthesis",):
            continue
        for md_file in sorted(topic_dir.glob("*.md")):
            name = md_file.name
            if name.startswith("SYNTHESIS-"):
                continue
            d = _parse_date(name)
            if d is None or d >= cutoff:
                continue
            rel = manifest_mod.rel_path(md_file, output_dir)
            if rel not in done:  # invariant: only move synthesized
                continue
            if dry_run:
                moved.append(rel)
                continue
            dest = topic_dir / "archive" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(md_file), str(dest))
            moved.append(rel)
    return moved


def main():
    from config import Settings
    s = Settings.load(Path(__file__).parent / "config.yaml", Path(__file__).parent / ".env")
    out = s.output_dir
    dry = "--dry-run" in sys.argv
    moved = run(out, out / "synthesized.txt",
                today=datetime.now().date(), keep_days=14, dry_run=dry)
    print(f"[archiver] {'(dry-run) would move' if dry else 'moved'} {len(moved)} files")
    for r in moved:
        print("  " + r)


if __name__ == "__main__":
    main()
