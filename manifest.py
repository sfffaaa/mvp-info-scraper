"""Manifest: tracks which articles have been synthesized (append-only)."""
from pathlib import Path


def load(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()
    return {
        ln.strip()
        for ln in manifest_path.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    }


def append(manifest_path: Path, rel_paths: list[str]) -> None:
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
