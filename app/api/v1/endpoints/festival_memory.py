# Re-export from backend/ops so main app router can keep including festival_memory.
# Follow-up: after ops is deployed and verified, remove this file and drop festival_memory from app/api/v1/router.py (see TASKS.md, ops platform task).
from backend.ops.api.v1 import festival_memory as _fm

router = _fm.router
festival_memory_service = _fm.festival_memory_service
asyncio = _fm.asyncio
run_festival_memory_extraction = _fm.run_festival_memory_extraction

__all__ = ["router", "festival_memory_service", "asyncio", "run_festival_memory_extraction"]
