from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import cyclopts
from loguru import logger
from pydantic import ValidationError

from research.amcp.core import (
    AccessDecision,
    AccessRequest,
    ConsentGrant,
    MemoryCustodian,
    MemoryRecord,
    build_demo_custodian,
    run_decision_trace,
    utc_now,
)


app = cyclopts.App(help="AMCP minimal reference implementation.")


@app.command
def demo() -> None:
    decisions = run_decision_trace()
    for step, decision in decisions:
        print(
            f"{step}: allowed={decision.allowed} reason={decision.reason} "
            f"missing={decision.missing_owner_consents}"
        )


@app.command
def export_demo(output: str = "research/amcp/demo_bundle.json") -> None:
    custodian, memory_id = build_demo_custodian()
    runner = "did:runner:coding-agent-v1"
    custodian.grant(
        ConsentGrant(
            owner_did="did:plc:alice",
            grantee_runner_did=runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    bundle = custodian.export_bundle()
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    print(f"Saved bundle to {output_path}")


@app.command
def self_test() -> None:
    decisions = dict(run_decision_trace())
    assert decisions["original-purpose"].allowed is True
    assert decisions["cross-purpose-without-consent"].allowed is False
    assert decisions["cross-purpose-only-alice-consented"].allowed is False
    assert decisions["cross-purpose-all-owners-consented"].allowed is True
    assert decisions["cross-purpose-after-bob-revocation"].allowed is False
    try:
        MemoryRecord(
            owner_dids=[],
            runner_did="did:runner:any",
            original_purpose="coding_assistant",
            content="x",
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("MemoryRecord owner_dids must not be empty.")

    custodian = MemoryCustodian()
    memory = custodian.add_memory(
        MemoryRecord(
            owner_dids=["did:plc:alice"],
            runner_did="did:runner:coding-agent-v1",
            original_purpose="coding_assistant",
            content="single owner memory",
        )
    )
    expired_consent = custodian.grant(
        ConsentGrant(
            owner_did="did:plc:alice",
            grantee_runner_did="did:runner:coding-agent-v1",
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory.memory_id,
            expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
        )
    )
    backdated_request = AccessRequest(
        memory_id=memory.memory_id,
        requester_runner_did="did:runner:coding-agent-v1",
        purpose="marketing_analytics",
        requested_at=datetime(1999, 1, 1, tzinfo=timezone.utc),
    )
    decision = custodian.evaluate_access(backdated_request)
    assert expired_consent.matches(backdated_request, evaluated_at=utc_now()) is False
    assert decision.allowed is False
    assert decision.missing_owner_consents == ["did:plc:alice"]
    print("AMCP self-test passed.")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
