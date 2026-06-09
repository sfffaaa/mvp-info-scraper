"""One-time backlog bootstrap: mark already-digested articles synthesized, detect gaps."""
import re
import sys
from pathlib import Path
from datetime import date, datetime, timedelta

import manifest as manifest_mod

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")
SYN_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-synthesis\.md$")


def uncovered_dates(synthesis_dir: Path, lookback: int, start: date, end: date) -> set:
    covered = set()
    for f in synthesis_dir.glob("*-synthesis.md"):
        m = SYN_RE.match(f.name)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        for k in range(lookback + 1):  # digest dated d covers [d-lookback, d]
            covered.add(d - timedelta(days=k))
    out = set()
    cur = start
    while cur <= end:
        if cur not in covered:
            out.add(cur)
        cur += timedelta(days=1)
    return out


def all_dated_articles(output_dir: Path) -> list[str]:
    res = []
    for topic_dir in output_dir.iterdir():
        if not topic_dir.is_dir() or topic_dir.name in ("synthesis",):
            continue
        for md in topic_dir.glob("*.md"):
            if md.name.startswith("SYNTHESIS-"):
                continue
            if not DATE_RE.match(md.name):
                continue
            res.append(manifest_mod.rel_path(md, output_dir))
    return res


def gap_article_rels(output_dir: Path, gaps: set) -> set:
    gapstr = {g.strftime("%Y-%m-%d") for g in gaps}
    return {r for r in all_dated_articles(output_dir) if r.split("/")[-1][:10] in gapstr}


def bootstrap(output_dir: Path):
    """manifest = all dated articles MINUS gap articles."""
    syn = output_dir / "synthesis"
    all_rels = all_dated_articles(output_dir)
    if not all_rels:
        return [], [], []
    dates = sorted({
        datetime.strptime(r.split("/")[-1][:10], "%Y-%m-%d").date() for r in all_rels
    })
    gaps = uncovered_dates(syn, lookback=2, start=dates[0], end=dates[-1])
    gap_rels = gap_article_rels(output_dir, gaps)
    keep = [r for r in all_rels if r not in gap_rels]
    return keep, sorted(gap_rels), sorted(gaps)


def main():
    from config import Settings
    s = Settings.load(Path(__file__).parent / "config.yaml", Path(__file__).parent / ".env")
    out = s.output_dir
    keep, gap_rels, gaps = bootstrap(out)
    print(f"[backlog] dated articles: {len(keep) + len(gap_rels)}")
    print(f"[backlog] gap dates ({len(gaps)}): {[g.isoformat() for g in gaps]}")
    print(f"[backlog] gap articles to deep-synthesize: {len(gap_rels)}")
    if "--write" in sys.argv:
        manifest_mod.append(out / "synthesized.txt", keep)
        print(f"[backlog] bootstrapped manifest with {len(keep)} articles (gaps excluded)")
    else:
        print("[backlog] dry-run. add --write to bootstrap manifest")


if __name__ == "__main__":
    main()
