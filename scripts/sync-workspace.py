"""Verify sibling polyrepo meta-workspace against workspace.manifest.json."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

CONTROL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = CONTROL_ROOT.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true", help="Check LATER repos in addition to V1")
    parser.add_argument("--check-clean", action="store_true", help="Fail if any repo has uncommitted changes")
    args = parser.parse_args()

    manifest = json.loads((CONTROL_ROOT / "workspace.manifest.json").read_text(encoding="utf-8"))
    pinned_ver = manifest["contracts_version"]
    errors = []

    for repo in manifest["repositories"]:
        if not args.all and repo["scope"] != "V1":
            continue
        rdir = WORKSPACE_ROOT / repo["name"]
        if not rdir.exists():
            errors.append(f"MISSING: {repo['name']} (expected at {rdir})")
            continue
        meta_path = rdir / "repo-meta.json"
        if not meta_path.exists():
            errors.append(f"MISSING repo-meta.json in {repo['name']}")
        else:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("contracts_version") != pinned_ver:
                errors.append(f"DRIFT in {repo['name']}: contracts_version={meta.get('contracts_version')} != {pinned_ver}")
        branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=rdir, capture_output=True, text=True).stdout.strip()
        if branch != repo["default_branch"]:
            print(f"WARN: {repo['name']} on branch {branch} (default: {repo['default_branch']})")
        if args.check_clean:
            st = subprocess.run(["git", "status", "--porcelain"], cwd=rdir, capture_output=True, text=True).stdout.strip()
            if st:
                errors.append(f"DIRTY worktree in {repo['name']}")

    if errors:
        print("FAIL:")
        for e in errors:
            print(" -", e)
        return 1
    print(f"PASS: Meta-workspace verified against workspace.manifest.json (contracts_version={pinned_ver})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
