# Agentic kernel architecture review

Reviewed `docs/agentic_kernel/ARCH.md` against the current production companion code path and recorded the designated architecture plus code-alignment TODOs.

- Confirmed production companion semantics are rooted in `CompanionManager` / `CompanionSession` calling `companion/turn.py::run_turn`, not `runtime/TurnOrchestrator`.
- Updated `ARCH.md` with design critique, current boundary deviations, an explicit event consistency contract, and implementation index corrections.
- Added `docs/agentic_kernel/todos/AGENTIC_KERNEL_ARCH_CODE_ALIGNMENT.md` for follow-up code tasks.

Follow-ups:

- Implement the code-alignment TODOs in priority order, starting with the companion turn contract and event consistency tests.
