from __future__ import annotations

import cyclopts

from research.amcp.adapters import run_langgraph_amcp_flow
from research.amcp.core import ConsentGrant, build_demo_custodian


app = cyclopts.App(help="AMCP LangGraph integration example.")


@app.command
def demo_original() -> None:
    custodian, memory_id = build_demo_custodian()
    state = run_langgraph_amcp_flow(
        custodian=custodian,
        runner_did="did:runner:coding-agent-v1",
        memory_id=memory_id,
        purpose="coding_assistant",
    )
    print(
        f"allowed={state['allowed']} "
        f"route={state['route']} "
        f"response={state['response']}"
    )


@app.command
def demo_denied() -> None:
    custodian, memory_id = build_demo_custodian()
    state = run_langgraph_amcp_flow(
        custodian=custodian,
        runner_did="did:runner:coding-agent-v1",
        memory_id=memory_id,
        purpose="marketing_analytics",
    )
    print(
        f"allowed={state['allowed']} "
        f"route={state['route']} "
        f"response={state['response']}"
    )


@app.command
def demo_consented() -> None:
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
    custodian.grant(
        ConsentGrant(
            owner_did="did:plc:bob",
            grantee_runner_did=runner,
            purpose="marketing_analytics",
            scope="single_memory",
            memory_id=memory_id,
        )
    )
    state = run_langgraph_amcp_flow(
        custodian=custodian,
        runner_did=runner,
        memory_id=memory_id,
        purpose="marketing_analytics",
    )
    print(
        f"allowed={state['allowed']} "
        f"route={state['route']} "
        f"response={state['response']}"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
