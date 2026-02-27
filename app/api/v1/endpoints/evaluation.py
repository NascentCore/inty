# Re-export from backend/ops so main app router can keep including evaluation.
# Follow-up: after ops is deployed and verified, remove this file and drop evaluation from app/api/v1/router.py (see TASKS.md, ops platform task).
from backend.ops.api.v1.evaluation import router

__all__ = ["router"]
