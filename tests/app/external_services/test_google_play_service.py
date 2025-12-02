# CREATED_BY_AGENT
from app.core.config import GooglePlayConfig
from app.external_services.google_play_service import GooglePlayService
from app.schemas.version import VersionReminderAction


def test_version_check_short_circuits_when_disabled():
    config = GooglePlayConfig(enable_version_check=False)
    service = GooglePlayService(android_publisher_service=None, config=config)

    def _fail():
        raise AssertionError("版本检查禁用时不应获取版本信息")

    service.get_app_version_info = _fail  # type: ignore[assignment]

    result = service.check_version_requirement(client_version_code=123)

    assert result["update_required"] is False
    assert result["force_update"] is False
    assert result["message"] == "Version check disabled"
    assert result["reminder_action"] == VersionReminderAction.SETTINGS_REMINDER


def test_version_check_uses_injected_min_supported_version():
    config = GooglePlayConfig(
        enable_version_check=True,
        min_supported_version=150,
        package_name="com.test.app",
    )
    service = GooglePlayService(android_publisher_service=None, config=config)

    def _fake_version_info():
        return {
            "version_name": "2.0.0",
            "version_code": 200,
            "release_notes": "Important fixes",
        }

    service.get_app_version_info = _fake_version_info  # type: ignore[assignment]

    result = service.check_version_requirement(client_version_code=120)

    assert result["force_update"] is True
    assert result["minimum_version"] == "150"
    assert result["reminder_action"] == VersionReminderAction.BLOCK_ACCESS
    assert result["latest_version"] == "2.0.0"
