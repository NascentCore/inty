from app.core.build_info import build_time_utc, vcs_dirty, vcs_revision
from app.core.config import global_config_loaded_from_config_yaml
from app.schemas.health import HealthCheckData


def build_health_check_data(*, ops: bool = False) -> HealthCheckData:
    cfg = global_config_loaded_from_config_yaml.app
    app_name = f"{cfg.name} Ops" if ops else cfg.name
    return HealthCheckData(
        app_name=app_name,
        version=cfg.version,
        environment=cfg.environment.value,
        vcs_revision=vcs_revision(),
        vcs_dirty=vcs_dirty(),
        build_time_utc=build_time_utc(),
    )
