"""Archiver: move synthesized + older-than-keep_days articles into <folder>/archive/."""
import shutil
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

import manifest as manifest_mod


def run(output_dir: Path, manifest_path: Path, today: date,
        keep_days: int = 14, dry_run: bool = False) -> list[str]:
    done = manifest_mod.load(manifest_path)
    cutoff = today - timedelta(days=keep_days)
    moved = []
    for md_file in manifest_mod.iter_dated_articles(output_dir):
        d = manifest_mod.parse_article_date(md_file.name)
        if d >= cutoff:
            continue
        rel = manifest_mod.rel_path(md_file, output_dir)
        if rel not in done:  # invariant: only move synthesized
            continue
        if dry_run:
            moved.append(rel)
            continue
        dest = md_file.parent / "archive" / md_file.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():  # no-clobber: never overwrite an already-archived copy
            print(f"[archiver] skip (archive exists): {rel}", file=sys.stderr)
            continue
        shutil.move(str(md_file), str(dest))
        moved.append(rel)
    return moved


def main():
    from config import Settings
    s = Settings.load(Path(__file__).parent / "config.yaml", Path(__file__).parent / ".env")
    out = s.output_dir
    dry = "--dry-run" in sys.argv
    moved = run(out, manifest_mod.default_path(out),
                today=datetime.now().date(), keep_days=14, dry_run=dry)
    print(f"[archiver] {'(dry-run) would move' if dry else 'moved'} {len(moved)} files")
    for r in moved:
        print("  " + r)


if __name__ == "__main__":
    main()
