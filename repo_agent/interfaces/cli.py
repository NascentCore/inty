from __future__ import annotations

from pathlib import Path
from typing import Any

import cyclopts
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
IDENTITY_DIR = REPO_ROOT / "repo_agent" / "identity"
SELF_MODEL_DIR = REPO_ROOT / "repo_agent" / "self_model"
GOVERNANCE_DIR = REPO_ROOT / "repo_agent" / "governance"

app = cyclopts.App(name="repo_agent")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _read_yaml(path: Path) -> dict[str, Any]:
    content = yaml.safe_load(path.read_text(encoding="utf-8"))
    if content is None:
        return {}
    assert isinstance(content, dict), f"invalid yaml object at {path}"
    return content


@app.command(name="whoami")
def whoami() -> None:
    """Explain repo agent mission and persona."""
    mission = _read_text(IDENTITY_DIR / "mission.md")
    persona = _read_text(IDENTITY_DIR / "persona.md")
    constitution = _read_text(IDENTITY_DIR / "constitution.md")
    print("=== WHO I AM ===")
    print(mission)
    print("")
    print("=== HOW I SPEAK ===")
    print(persona)
    print("")
    print("=== MY CONSTITUTION ===")
    print(constitution)


@app.command(name="capabilities")
def capabilities() -> None:
    """List current capabilities from self_model."""
    data = _read_yaml(SELF_MODEL_DIR / "capabilities.yaml")
    items = data.get("capabilities", [])
    assert isinstance(items, list), "capabilities must be a list"
    print("=== WHAT I CAN DO NOW ===")
    for item in items:
        assert isinstance(item, dict), "capability entry must be mapping"
        cap_id = item.get("id", "")
        mode = item.get("mode", "")
        enabled = item.get("enabled", False)
        desc = item.get("description", "")
        print(f"- [{mode}] {cap_id} (enabled={enabled}): {desc}")


@app.command(name="boundaries")
def boundaries() -> None:
    """Show change-policy and release gates."""
    policy = _read_yaml(GOVERNANCE_DIR / "change_policy.yaml")
    gates = _read_yaml(GOVERNANCE_DIR / "release_gates.yaml")
    policy_block = policy.get("policy", {})
    print("=== BOUNDARIES ===")
    print("deny_paths:")
    for path in policy_block.get("deny_paths", []):
        print(f"- {path}")
    print("")
    print("high_risk_paths:")
    for path in policy_block.get("high_risk_paths", []):
        print(f"- {path}")
    print("")
    print("allowed_write_scopes:")
    for path in policy_block.get("allowed_write_scopes", []):
        print(f"- {path}")
    print("")
    print("rules:")
    for rule_name, rule_value in policy.get("rules", {}).items():
        print(f"- {rule_name}: {rule_value}")
    print("")
    print("release_gates:")
    for gate_name, checks in gates.get("release_gates", {}).items():
        print(f"- {gate_name}:")
        for check in checks:
            print(f"  - {check}")


@app.command(name="status")
def status() -> None:
    """Report current phase and next actions."""
    map_data = _read_yaml(SELF_MODEL_DIR / "system_map.yaml")
    print("=== WHAT CHANGED RECENTLY ===")
    print("Bootstrap created: identity + self_model + governance + decision log.")
    print("")
    print("=== WHAT I PROPOSE NEXT ===")
    print("- Build runtime/orchestrator bridge to existing agentic kernel tools.")
    print("- Add observe/diagnose proposal artifacts per iteration.")
    print("- Keep scope on repo_agent docs and interfaces until gates mature.")
    print("")
    print("=== CURRENT SYSTEM MAP DOMAINS ===")
    for domain in map_data.get("domains", []):
        assert isinstance(domain, dict), "domain entry must be mapping"
        print(f"- {domain.get('name')}: {domain.get('role')}")


if __name__ == "__main__":
    app()
