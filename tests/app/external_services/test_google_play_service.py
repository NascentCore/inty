# CREATED_BY_AGENT
from datetime import datetime, timezone

import pytest

from app.core.config import GooglePlayConfig
from app.external_services.fakes.android_publisher import FakeAndroidPublisher
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
    assert result["reminder_action"] == VersionReminderAction.NONE


@pytest.fixture
def google_play_config():
    """创建测试用的 GooglePlayConfig"""
    return GooglePlayConfig(
        package_name="com.ai.intellimate",
        enable_version_check=True,
        # 生产环境会通过配置文件设置 current_version_code（用于跳过 Google Play API）；
        # 但单元测试默认应覆盖为 0，以便走 FakeAndroidPublisher 的 mocked 路径。
        current_version_code=0,
        min_supported_version=1,
        release_track="production",
        fallback_tracks=["production", "internal"],
    )


@pytest.fixture
def fake_service():
    """创建假 Google Play 服务"""
    return FakeAndroidPublisher()


@pytest.fixture
def google_play_service(fake_service, google_play_config):
    """创建 GooglePlayService 实例"""
    return GooglePlayService(
        android_publisher_service=fake_service, config=google_play_config
    )


class TestVerifySubscriptionPurchase:
    """测试 verify_subscription_purchase 方法"""

    def test_verify_subscription_success_valid(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试成功验证有效订阅"""
        product_id = "premium_monthly"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置有效订阅响应
        future_time = int((datetime.now(timezone.utc).timestamp() + 86400) * 1000)
        fake_service.set_subscription_response(
            package_name,
            product_id,
            purchase_token,
            {
                "paymentState": 1,  # 已支付
                "expiryTimeMillis": str(future_time),
                "startTimeMillis": "1704067200000",
                "autoRenewing": True,
            },
        )

        is_valid, purchase_info = google_play_service.verify_subscription_purchase(
            product_id, purchase_token
        )

        assert is_valid is True
        assert "error" not in purchase_info
        assert purchase_info["payment_state"] == 1
        assert purchase_info["expiry_time"] is not None

    def test_verify_subscription_expired(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试验证过期订阅"""
        product_id = "premium_monthly"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置过期订阅响应
        past_time = int((datetime.now(timezone.utc).timestamp() - 86400) * 1000)
        fake_service.set_subscription_response(
            package_name,
            product_id,
            purchase_token,
            {
                "paymentState": 1,
                "expiryTimeMillis": str(past_time),
                "startTimeMillis": "1704067200000",
            },
        )

        is_valid, purchase_info = google_play_service.verify_subscription_purchase(
            product_id, purchase_token
        )

        assert is_valid is False
        assert purchase_info["expiry_time"] < datetime.now(timezone.utc)

    def test_verify_subscription_pending_payment(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试验证待支付订阅"""
        product_id = "premium_monthly"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置待支付订阅响应
        future_time = int((datetime.now(timezone.utc).timestamp() + 86400) * 1000)
        fake_service.set_subscription_response(
            package_name,
            product_id,
            purchase_token,
            {
                "paymentState": 0,  # 待支付
                "expiryTimeMillis": str(future_time),
            },
        )

        is_valid, purchase_info = google_play_service.verify_subscription_purchase(
            product_id, purchase_token
        )

        assert is_valid is False
        assert purchase_info["payment_state"] == 0

    def test_verify_subscription_cancelled_in_grace_period(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试验证已取消但在宽限期内的订阅"""
        product_id = "premium_monthly"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置已取消但在宽限期内
        now = datetime.now(timezone.utc)
        cancellation_time = int((now.timestamp() - 3600) * 1000)  # 1小时前取消
        expiry_time = int((now.timestamp() + 3600) * 1000)  # 1小时后到期

        fake_service.set_subscription_response(
            package_name,
            product_id,
            purchase_token,
            {
                "paymentState": 1,
                "expiryTimeMillis": str(expiry_time),
                "userCancellationTimeMillis": str(cancellation_time),
                "cancelReason": 1,  # 用户取消
            },
        )

        is_valid, purchase_info = google_play_service.verify_subscription_purchase(
            product_id, purchase_token
        )

        assert is_valid is True  # 在宽限期内仍然有效
        assert purchase_info["cancel_reason"] is not None

    def test_verify_subscription_cancelled_outside_grace_period(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试验证已取消且不在宽限期的订阅"""
        product_id = "premium_monthly"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置已取消且不在宽限期内
        now = datetime.now(timezone.utc)
        cancellation_time = int((now.timestamp() - 7200) * 1000)  # 2小时前取消
        expiry_time = int((now.timestamp() - 3600) * 1000)  # 1小时前已到期

        fake_service.set_subscription_response(
            package_name,
            product_id,
            purchase_token,
            {
                "paymentState": 1,
                "expiryTimeMillis": str(expiry_time),
                "userCancellationTimeMillis": str(cancellation_time),
                "cancelReason": 1,
            },
        )

        is_valid, purchase_info = google_play_service.verify_subscription_purchase(
            product_id, purchase_token
        )

        assert is_valid is False  # 已过期且不在宽限期

    def test_verify_subscription_http_error_400(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试 HttpError 400（产品ID不匹配，应记录为 DEBUG）"""
        product_id = "invalid_product"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置 400 错误
        error = FakeAndroidPublisher.create_http_error(400, "Invalid product ID")
        fake_service.set_subscription_error(
            package_name, product_id, purchase_token, error
        )

        is_valid, purchase_info = google_play_service.verify_subscription_purchase(
            product_id, purchase_token
        )

        assert is_valid is False
        assert "error" in purchase_info

    def test_verify_subscription_http_error_other(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试 HttpError 其他状态码（应记录为 ERROR）"""
        product_id = "premium_monthly"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置 500 错误
        error = FakeAndroidPublisher.create_http_error(500, "Internal server error")
        fake_service.set_subscription_error(
            package_name, product_id, purchase_token, error
        )

        is_valid, purchase_info = google_play_service.verify_subscription_purchase(
            product_id, purchase_token
        )

        assert is_valid is False
        assert "error" in purchase_info

    def test_verify_subscription_general_exception(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试通用异常处理"""
        product_id = "premium_monthly"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置通用异常（通过修改 fake_service 的行为）
        original_get = fake_service._subscriptions.get

        def raise_exception(*args, **kwargs):
            raise ValueError("Unexpected error")

        fake_service._subscriptions.get = raise_exception

        try:
            is_valid, purchase_info = google_play_service.verify_subscription_purchase(
                product_id, purchase_token
            )

            assert is_valid is False
            assert "error" in purchase_info
        finally:
            # 恢复原始方法
            fake_service._subscriptions.get = original_get


class TestVerifyProductPurchase:
    """测试 verify_product_purchase 方法"""

    def test_verify_product_success_valid(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试成功验证有效购买"""
        product_id = "premium_one_time"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置有效购买响应
        fake_service.set_product_response(
            package_name,
            product_id,
            purchase_token,
            {
                "purchaseState": 0,  # 已购买
                "consumptionState": 0,  # 未消费
                "acknowledgementState": 1,  # 已确认
                "purchaseTimeMillis": "1704067200000",
            },
        )

        is_valid, purchase_info = google_play_service.verify_product_purchase(
            product_id, purchase_token
        )

        assert is_valid is True
        assert "error" not in purchase_info
        assert purchase_info["purchase_state"] == 0
        assert purchase_info["consumption_state"] == 0
        assert purchase_info["acknowledgement_state"] == 1

    def test_verify_product_cancelled(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试验证已取消的购买"""
        product_id = "premium_one_time"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置已取消的购买
        fake_service.set_product_response(
            package_name,
            product_id,
            purchase_token,
            {
                "purchaseState": 1,  # 已取消
                "consumptionState": 0,
                "acknowledgementState": 1,
            },
        )

        is_valid, purchase_info = google_play_service.verify_product_purchase(
            product_id, purchase_token
        )

        assert is_valid is False
        assert purchase_info["purchase_state"] == 1

    def test_verify_product_consumed(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试验证已消费的购买"""
        product_id = "premium_one_time"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置已消费的购买
        fake_service.set_product_response(
            package_name,
            product_id,
            purchase_token,
            {
                "purchaseState": 0,
                "consumptionState": 1,  # 已消费
                "acknowledgementState": 1,
            },
        )

        is_valid, purchase_info = google_play_service.verify_product_purchase(
            product_id, purchase_token
        )

        assert is_valid is False
        assert purchase_info["consumption_state"] == 1

    def test_verify_product_unacknowledged(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试验证未确认的购买"""
        product_id = "premium_one_time"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置未确认的购买
        fake_service.set_product_response(
            package_name,
            product_id,
            purchase_token,
            {
                "purchaseState": 0,
                "consumptionState": 0,
                "acknowledgementState": 0,  # 未确认
            },
        )

        is_valid, purchase_info = google_play_service.verify_product_purchase(
            product_id, purchase_token
        )

        assert is_valid is False
        assert purchase_info["acknowledgement_state"] == 0

    def test_verify_product_http_error(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试 HttpError 处理"""
        product_id = "invalid_product"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置 400 错误
        error = FakeAndroidPublisher.create_http_error(400, "Invalid product ID")
        fake_service.set_product_error(package_name, product_id, purchase_token, error)

        is_valid, purchase_info = google_play_service.verify_product_purchase(
            product_id, purchase_token
        )

        assert is_valid is False
        assert "error" in purchase_info

    def test_verify_product_general_exception(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试通用异常处理"""
        product_id = "premium_one_time"
        purchase_token = "test_token_123"
        package_name = google_play_config.package_name

        # 设置通用异常 - 通过修改 fake_service 的 products.get 方法
        original_get = fake_service._products.get

        def raise_exception(*args, **kwargs):
            raise ValueError("Unexpected error")

        fake_service._products.get = raise_exception

        try:
            is_valid, purchase_info = google_play_service.verify_product_purchase(
                product_id, purchase_token
            )

            assert is_valid is False
            assert "error" in purchase_info
        finally:
            # 恢复原始方法
            fake_service._products.get = original_get


class TestCheckVersionRequirement:
    """测试 check_version_requirement 方法"""

    def test_version_check_disabled(self, fake_service, google_play_config):
        """测试版本检查被禁用时的行为"""
        config = GooglePlayConfig(
            package_name=google_play_config.package_name,
            enable_version_check=False,
            current_version_code=0,
        )
        service = GooglePlayService(
            android_publisher_service=fake_service, config=config
        )

        result = service.check_version_requirement(100)

        assert result["update_required"] is False
        assert result["force_update"] is False
        assert result["message"] == "Version check disabled"

    def test_version_check_update_required(self, fake_service, google_play_config):
        """测试客户端版本低于最新版本（建议更新）"""
        config = GooglePlayConfig(
            package_name=google_play_config.package_name,
            enable_version_check=True,
            current_version_code=0,
            min_supported_version=1,
        )
        service = GooglePlayService(
            android_publisher_service=fake_service, config=config
        )
        package_name = config.package_name

        # 设置版本信息
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "production",
            {
                "releases": [
                    {
                        "versionCodes": ["100"],
                        "name": "2.0.0",
                        "status": "completed",
                    }
                ]
            },
        )

        result = service.check_version_requirement(50)

        assert result["update_required"] is True
        assert result["force_update"] is False
        assert result["message"] == "New version available"
        assert result["latest_version_code"] == 100  # versionCodes 返回字符串

    def test_version_check_up_to_date(self, fake_service, google_play_config):
        """测试客户端版本等于最新版本（无需更新）"""
        config = GooglePlayConfig(
            package_name=google_play_config.package_name,
            enable_version_check=True,
            current_version_code=0,
            min_supported_version=1,
        )
        service = GooglePlayService(
            android_publisher_service=fake_service, config=config
        )
        package_name = config.package_name

        # 设置版本信息
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "production",
            {
                "releases": [
                    {
                        "versionCodes": ["100"],
                        "name": "2.0.0",
                        "status": "completed",
                    }
                ]
            },
        )

        result = service.check_version_requirement(100)

        assert result["update_required"] is False
        assert result["force_update"] is False
        assert result["message"] == "App is up to date"

    def test_version_check_unable_to_fetch_version(
        self, fake_service, google_play_config
    ):
        """测试无法获取版本信息时的降级处理"""
        config = GooglePlayConfig(
            package_name=google_play_config.package_name,
            enable_version_check=True,
            current_version_code=0,
        )
        service = GooglePlayService(
            android_publisher_service=fake_service, config=config
        )
        package_name = config.package_name

        # 设置编辑错误
        error = FakeAndroidPublisher.create_http_error(500, "API Error")
        fake_service.set_edit_error(package_name, error)

        result = service.check_version_requirement(50)

        assert result["update_required"] is False
        assert result["force_update"] is False
        assert "error" in result
        assert result["message"] == "Unable to fetch version info"

    def test_version_check_compare_failure(self, fake_service, google_play_config):
        """测试版本比较失败时的保守处理（要求更新）"""
        config = GooglePlayConfig(
            package_name=google_play_config.package_name,
            enable_version_check=True,
            current_version_code=0,
            min_supported_version=1,
        )
        service = GooglePlayService(
            android_publisher_service=fake_service, config=config
        )
        package_name = config.package_name

        # 设置无效的版本代码（字符串而非数字）
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "production",
            {
                "releases": [
                    {
                        "versionCodes": ["invalid"],
                        "name": "2.0.0",
                        "status": "completed",
                    }
                ]
            },
        )

        result = service.check_version_requirement(50)

        # 版本比较失败时，保守起见要求更新
        assert result["update_required"] is False


class TestGetAppVersionInfo:
    """测试 get_app_version_info 方法"""

    def test_get_version_info_uses_config_override(
        self, fake_service, google_play_config
    ):
        """测试配置 current_version_code 时会跳过 Google Play API 并返回覆盖值"""
        override_code = 2949
        config = GooglePlayConfig(
            package_name=google_play_config.package_name,
            enable_version_check=True,
            current_version_code=override_code,
            release_track="production",
            fallback_tracks=["production", "internal"],
        )
        service = GooglePlayService(
            android_publisher_service=fake_service, config=config
        )

        version_info = service.get_app_version_info()

        assert "error" not in version_info
        assert version_info["version_code"] == override_code
        assert version_info["track"] == "config_override"

    def test_get_version_info_success_primary_track(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试从主轨道成功获取版本信息"""
        package_name = google_play_config.package_name

        # 设置主轨道响应
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "production",
            {
                "releases": [
                    {
                        "versionCodes": ["100"],
                        "name": "2.0.0",
                        "status": "completed",
                        "releaseNotes": [
                            {"language": "zh-CN", "text": "中文更新日志"},
                            {"language": "en-US", "text": "English release notes"},
                        ],
                    }
                ]
            },
        )

        version_info = google_play_service.get_app_version_info()

        assert "error" not in version_info
        assert version_info["version_code"] == "100"  # versionCodes 返回字符串
        assert version_info["version_name"] == "2.0.0"
        assert version_info["track"] == "production"
        assert version_info["release_notes"] == "中文更新日志"  # 优先返回中文

    def test_get_version_info_fallback_track(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试主轨道失败时回退到备用轨道"""
        package_name = google_play_config.package_name

        # 设置主轨道错误
        error = FakeAndroidPublisher.create_http_error(404, "Track not found")
        fake_service.set_track_error(package_name, "edit_1", "production", error)

        # 设置备用轨道响应
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "internal",
            {
                "releases": [
                    {
                        "versionCodes": ["95"],
                        "name": "1.9.5",
                        "status": "completed",
                    }
                ]
            },
        )

        version_info = google_play_service.get_app_version_info()

        assert "error" not in version_info
        assert version_info["version_code"] == "95"  # versionCodes 返回字符串
        assert version_info["track"] == "internal"

    def test_get_version_info_all_tracks_fail(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试所有轨道都失败时的处理"""
        package_name = google_play_config.package_name

        # 设置所有轨道错误
        error = FakeAndroidPublisher.create_http_error(404, "Track not found")
        fake_service.set_track_error(package_name, "edit_1", "production", error)
        fake_service.set_track_error(package_name, "edit_1", "internal", error)

        version_info = google_play_service.get_app_version_info()

        assert "error" in version_info
        assert "No releases found" in version_info["error"]

    def test_get_version_info_no_releases(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试轨道没有版本信息"""
        package_name = google_play_config.package_name

        # 设置空响应 - 需要为所有轨道设置空响应
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "production",
            {"releases": []},
        )
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "internal",
            {"releases": []},
        )

        version_info = google_play_service.get_app_version_info()

        assert "error" in version_info
        assert "No releases found" in version_info["error"]

    def test_get_version_info_edit_error(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试编辑会话创建失败"""
        package_name = google_play_config.package_name

        # 设置编辑错误
        error = FakeAndroidPublisher.create_http_error(500, "API Error")
        fake_service.set_edit_error(package_name, error)

        version_info = google_play_service.get_app_version_info()

        assert "error" in version_info
        assert "API Error" in version_info["error"]

    def test_get_version_info_release_notes_english_fallback(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试发布说明回退到英文"""
        package_name = google_play_config.package_name

        # 设置只有英文的发布说明
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "production",
            {
                "releases": [
                    {
                        "versionCodes": ["100"],
                        "name": "2.0.0",
                        "status": "completed",
                        "releaseNotes": [
                            {"language": "en-US", "text": "English release notes"}
                        ],
                    }
                ]
            },
        )

        version_info = google_play_service.get_app_version_info()

        assert version_info["release_notes"] == "English release notes"

    def test_get_version_info_release_notes_none(
        self, google_play_service, fake_service, google_play_config
    ):
        """测试没有发布说明"""
        package_name = google_play_config.package_name

        # 设置没有发布说明
        fake_service.set_track_response(
            package_name,
            "edit_1",
            "production",
            {
                "releases": [
                    {
                        "versionCodes": ["100"],
                        "name": "2.0.0",
                        "status": "completed",
                    }
                ]
            },
        )

        version_info = google_play_service.get_app_version_info()

        assert version_info["release_notes"] is None
