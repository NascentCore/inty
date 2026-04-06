from pydantic import BaseModel


class HealthCheckData(BaseModel):
    """Health / build identity exposed on unauthenticated root or /health routes."""

    app_name: str
    version: str
    environment: str
    vcs_revision: str
    vcs_dirty: bool
    build_time_utc: str
