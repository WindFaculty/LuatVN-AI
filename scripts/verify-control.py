"""Verify G0 docs integrity: SHA-256 manifest, RTM 123 IDs, links, and workspace manifest."""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
G0 = ROOT / "docs" / "g0"

# 1. Verify SHA-256 manifest
sha_file = G0 / "g0-v0.2.1.sha256"
for line in sha_file.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    expected, rel = line.split("  ", 1)
    actual = hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
    assert actual == expected, f"SHA-256 mismatch for {rel}: {actual} != {expected}"

# 2. Verify RTM 123 baseline IDs
pat = r"\b(?:REQ-[A-Z]+-\d+|BR-[A-Z]+-\d+|NFR-\d+|AC-\d+|DEC-\d+|OBJ-\d+)\b"
b_ids = set(re.findall(pat, (ROOT / "Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md").read_text(encoding="utf-8")))
r_ids = set(re.findall(pat, (G0 / "rtm.md").read_text(encoding="utf-8")))
assert b_ids == r_ids, f"RTM mismatch: missing={b_ids - r_ids}, extra={r_ids - b_ids}"

# 3. Verify all internal markdown links inside docs/g0/
for fp in G0.rglob("*.md"):
    txt = fp.read_text(encoding="utf-8")
    for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", txt):
        t = m.group(2)
        if t.startswith("http"):
            continue
        p, _, _ = t.partition("#")
        full = (fp.parent / p).resolve() if p else fp
        assert full.exists(), f"Broken link in {fp.relative_to(ROOT)} -> {t}"

# 4. Verify workspace.manifest.json
manifest = json.loads((ROOT / "workspace.manifest.json").read_text(encoding="utf-8"))
assert len(manifest["repositories"]) == 16
assert all(r["visibility"] == "PRIVATE" for r in manifest["repositories"])
assert all(r["name"].startswith("LuatVN-AI-") for r in manifest["repositories"])

print(f"PASS: Control repo verified (SHA-256 OK, RTM={len(r_ids)}/123, 16 PRIVATE repos in manifest)")
