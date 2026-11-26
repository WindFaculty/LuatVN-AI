"""Verify the approved G0 evidence and the current monorepo checkout."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
G0 = ROOT / "docs/g0"
ID_PATTERN = re.compile(r"\b(?:REQ-[A-Z]+-\d+|BR-[A-Z]+-\d+|NFR-\d+|AC-\d+|DEC-\d+|OBJ-\d+)\b")
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
SECRET_PATTERN = re.compile(r"AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|AIza[0-9A-Za-z_-]{35}|-----BEGIN (?:RSA|EC|OPENSSH) PRIVATE KEY-----")


def verify_g0(current_baseline: Path) -> None:
    checks = (G0 / "g0-v0.2.1.sha256").read_text(encoding="utf-8").splitlines()
    assert len(checks) == 25, "Expected all 25 evidence hashes from the approved G0 snapshot"
    for line in checks:
        expected, filename = line.split("  ", 1)
        actual = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
        assert actual == expected, f"G0 evidence changed: {filename}"

    original_baseline = ROOT / "Luat_Viet_Nam_AI_Requirements_Baseline_v1.0.md"
    files = (original_baseline, current_baseline, G0 / "rtm.md")
    original_ids, current_ids, rtm_ids = (set(ID_PATTERN.findall(path.read_text(encoding="utf-8"))) for path in files)
    assert len(original_ids) == 123 and original_ids == current_ids == rtm_ids, "Baseline/RTM ID mismatch"


def verify_links(files: list[Path]) -> None:
    for path in files:
        for target in LINK_PATTERN.findall(path.read_text(encoding="utf-8")):
            if target.startswith(("http://", "https://")):
                continue
            filename = target.partition("#")[0]
            resolved = (path.parent / filename).resolve() if filename else path
            assert resolved.is_relative_to(ROOT) and resolved.exists(), f"Broken link in {path.relative_to(ROOT)}: {target}"


def verify_tracked_files() -> None:
    index = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT, encoding="utf-8")
    for entry in filter(None, index.split("\0")):
        info, filename = entry.split("\t", 1)
        assert not info.startswith("160000 "), f"Gitlink in monorepo: {filename}"
        path = ROOT / filename
        if path.is_file():
            assert not SECRET_PATTERN.search(path.read_text(encoding="utf-8", errors="ignore")), f"Possible secret in {filename}"


def verify_components(manifest: dict, run_smoke: bool) -> None:
    paths = [component["path"] for component in manifest["components"]]
    assert len(paths) == len(set(paths)), "Duplicate component paths"
    assert set(paths) == {
        "apps/web", "apps/studio", "packages/contracts", "services/account-workspace",
        "services/data-ingestion", "services/legal-knowledge", "services/retrieval",
        "services/ai-orchestrator", "services/model-gateway", "services/evaluation",
    }, "V1 component catalog mismatch"
    assert not any(ROOT.glob("*/*/.git")), "Nested Git root in component checkout"
    for component in manifest["components"]:
        path = ROOT / component["path"]
        metadata = json.loads((path / "repo-meta.json").read_text(encoding="utf-8"))
        assert metadata["component_path"] == component["path"], path.name
        assert metadata["repository"] == f"https://github.com/{manifest['repository']}", path.name
        assert metadata["contracts_version"] == manifest["contracts_version"], f"Contract pin drift: {path.name}"
        assert metadata["kind"] == component["kind"], f"Component kind drift: {path.name}"
        verify_links([path / "README.md"])
        if run_smoke and component["kind"] == "python":
            env = {**os.environ, "PYTHONPATH": str(path / "src")}
            subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=path, env=env, check=True)
        elif run_smoke and component["kind"] == "frontend":
            npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
            if npm is None:
                raise RuntimeError("npm is required for frontend smoke checks")
            subprocess.run([npm, "test"], cwd=path, check=True)

    if manifest["contracts_version"] == "0.2.1-draft":
        for original in (G0 / "contracts").iterdir():
            current = ROOT / "packages/contracts/contracts" / original.name
            assert original.read_bytes() == current.read_bytes(), f"Contract changed without a version change: {current.name}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Also run service and app smoke tests")
    arguments = parser.parse_args()
    manifest = json.loads((ROOT / "workspace.manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "2.0"
    assert manifest["repository"] == "WindFaculty/LuatVN-AI"
    assert manifest["demo_repository"] == "WindFaculty/LuatVN-AI-demo"
    baseline = ROOT / manifest["baseline"]
    verify_g0(baseline)
    verify_links([ROOT / "README.md", baseline, *sorted((ROOT / "docs").rglob("*.md"))])
    verify_tracked_files()
    verify_components(manifest, arguments.smoke)
    print("PASS: 25 G0 digests, 123 RTM IDs, documentation links and 10 monorepo components")


if __name__ == "__main__":
    main()
