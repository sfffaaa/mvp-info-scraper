import manifest


def test_load_empty_returns_empty_set(tmp_path):
    assert manifest.load(tmp_path / "m.txt") == set()


def test_append_then_load_roundtrip(tmp_path):
    m = tmp_path / "m.txt"
    manifest.append(m, ["crypto/2026-06-01-a.md", "ai-tools/2026-06-01-b.md"])
    assert manifest.load(m) == {"crypto/2026-06-01-a.md", "ai-tools/2026-06-01-b.md"}


def test_append_dedups(tmp_path):
    m = tmp_path / "m.txt"
    manifest.append(m, ["crypto/x.md"])
    manifest.append(m, ["crypto/x.md", "crypto/y.md"])
    assert manifest.load(m) == {"crypto/x.md", "crypto/y.md"}


def test_rel_path_normalizes(tmp_path):
    out = tmp_path / "posts"
    (out / "crypto").mkdir(parents=True)
    f = out / "crypto" / "2026-06-01-a.md"
    f.write_text("x")
    assert manifest.rel_path(f, out) == "crypto/2026-06-01-a.md"
