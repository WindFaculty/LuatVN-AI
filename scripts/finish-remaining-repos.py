"""Create and push any remaining PRIVATE repos from workspace.manifest.json once GitHub rate limit resets."""
import json
import subprocess
import sys
from pathlib import Path

CONTROL_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = CONTROL_ROOT.parent

DESCRIPTIONS = {
    "LuatVN-AI-contracts": "Luat Viet Nam AI - OpenAPI 3.1, Internal JSON Schemas, Typed SDKs & Compatibility CI (V1)",
    "LuatVN-AI-document-intelligence": "Luat Viet Nam AI - Private Document Intelligence & Clause Comparison (LATER skeleton)",
    "LuatVN-AI-legal-monitoring": "Luat Viet Nam AI - Legal Change Monitoring, Subscriptions & Notifications (LATER skeleton)",
    "LuatVN-AI-billing-enterprise": "Luat Viet Nam AI - Billing, Entitlements & Enterprise Policies (LATER skeleton)",
    "LuatVN-AI-community": "Luat Viet Nam AI - Community Contributions & Moderation (LATER skeleton)",
    "LuatVN-AI-mobile": "Luat Viet Nam AI - Mobile App (React Native / Expo, Android then iOS) (LATER skeleton)",
}


def main() -> int:
    manifest = json.loads((CONTROL_ROOT / "workspace.manifest.json").read_text(encoding="utf-8"))
    ns = manifest["namespace"]
    pending = 0

    for repo in manifest["repositories"]:
        name = repo["name"]
        full = f"{ns}/{name}"
        exists = subprocess.run(["gh", "repo", "view", full, "--json", "name"], capture_output=True, text=True).returncode == 0
        if not exists:
            desc = DESCRIPTIONS.get(name, f"Luat Viet Nam AI - {name}")
            c = subprocess.run(["gh", "repo", "create", full, "--private", "--description", desc, "--disable-wiki"], capture_output=True, text=True)
            if c.returncode != 0:
                print(f"PENDING: {full} -> {c.stderr.strip()}")
                pending += 1
                continue
            print(f"CREATED: {full}")
        p = subprocess.run(["git", "push", "-u", "origin", "main"], cwd=WORKSPACE_ROOT / name, capture_output=True, text=True)
        if p.returncode != 0:
            print(f"PUSH_ERR: {full} -> {p.stderr.strip()}")
            pending += 1
        else:
            print(f"SYNCED:  {full}")

    if pending:
        print(f"\n{pending} repository(ies) still pending. Re-run after GitHub createRepository cooldown.")
        return 1
    print("\nPASS: All 16 PRIVATE repositories created and pushed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
