"""Fake Google Play API service for testing.

模拟 googleapiclient.discovery.Resource 的链式调用结构，用于单元测试。
"""

from typing import Any, Callable, Dict, Optional
from unittest.mock import MagicMock

from googleapiclient.errors import HttpError


class FakeGooglePlayService:
    """用于测试的假 Google Play API 服务。

    行为：
    - 模拟 googleapiclient.discovery.Resource 的链式调用结构
    - 支持预设响应数据和异常
    - 支持模拟 HttpError 异常（带状态码）

    使用示例：
        fake_service = FakeGooglePlayService()
        fake_service.set_subscription_response({"paymentState": 1, "expiryTimeMillis": "..."})
        service = GooglePlayService(fake_service)
    """

    def __init__(self):
        """初始化假服务"""
        self._subscription_responses: Dict[str, Dict[str, Any]] = {}
        self._product_responses: Dict[str, Dict[str, Any]] = {}
        self._subscription_errors: Dict[str, Optional[HttpError]] = {}
        self._product_errors: Dict[str, Optional[HttpError]] = {}
        self._edit_responses: Dict[str, Any] = {}
        self._track_responses: Dict[str, Dict[str, Any]] = {}
        self._edit_errors: Dict[str, Optional[HttpError]] = {}
        self._track_errors: Dict[str, Optional[HttpError]] = {}
        self._acknowledge_success: Dict[str, bool] = {}
        self._cancel_success: Dict[str, bool] = {}
        self._defer_success: Dict[str, bool] = {}
        self._acknowledge_errors: Dict[str, Optional[HttpError]] = {}
        self._cancel_errors: Dict[str, Optional[HttpError]] = {}
        self._defer_errors: Dict[str, Optional[HttpError]] = {}
        self._edit_id_counter = 0

        # 构建链式调用结构
        self._build_chain()

    def _build_chain(self):
        """构建链式调用结构"""
        # purchases().subscriptions().get().execute()
        self._purchases = MagicMock()
        
        # 使用普通对象而不是 MagicMock，避免属性被覆盖
        self._subscriptions = type('Subscriptions', (), {})()
        self._products = type('Products', (), {})()
        self._edits = MagicMock()

        # 设置链式调用
        self._purchases.subscriptions.return_value = self._subscriptions
        self._purchases.products.return_value = self._products

        # 订阅相关方法
        self._subscriptions.get = self._create_subscription_get()
        self._subscriptions.acknowledge = self._create_subscription_acknowledge()
        self._subscriptions.cancel = self._create_subscription_cancel()
        self._subscriptions.defer = self._create_subscription_defer()

        # 产品相关方法
        self._products.get = self._create_product_get()

        # edits 相关方法
        self._edits.insert = self._create_edit_insert()
        self._edits.delete = self._create_edit_delete()
        self._edits.tracks = MagicMock()
        self._tracks = MagicMock()
        self._edits.tracks.return_value = self._tracks
        self._tracks.get = self._create_track_get()

    def purchases(self):
        """返回 purchases 对象"""
        return self._purchases

    def edits(self):
        """返回 edits 对象"""
        return self._edits

    def _create_subscription_get(self) -> Callable:
        """创建订阅获取方法"""

        def get(packageName: str, subscriptionId: str, token: str):
            key = f"{packageName}:{subscriptionId}:{token}"

            # 检查是否有预设的错误
            if key in self._subscription_errors and self._subscription_errors[key] is not None:
                raise self._subscription_errors[key]

            # 返回预设的响应
            if key in self._subscription_responses:
                response = self._subscription_responses[key]
            else:
                # 默认响应
                response = {
                    "paymentState": 1,
                    "expiryTimeMillis": "1735689600000",  # 2025-01-01
                    "startTimeMillis": "1704067200000",  # 2024-01-01
                    "autoRenewing": True,
                }

            mock_request = MagicMock()
            mock_request.execute.return_value = response
            return mock_request

        return get

    def _create_product_get(self) -> Callable:
        """创建产品获取方法"""

        def get(packageName: str, productId: str, token: str):
            key = f"{packageName}:{productId}:{token}"

            # 检查是否有预设的错误
            if key in self._product_errors and self._product_errors[key] is not None:
                raise self._product_errors[key]

            # 返回预设的响应
            if key in self._product_responses:
                response = self._product_responses[key]
            else:
                # 默认响应
                response = {
                    "purchaseState": 0,
                    "consumptionState": 0,
                    "acknowledgementState": 1,
                    "purchaseTimeMillis": "1704067200000",
                }

            mock_request = MagicMock()
            mock_request.execute.return_value = response
            return mock_request

        return get

    def _create_subscription_acknowledge(self) -> Callable:
        """创建订阅确认方法"""

        def acknowledge(packageName: str, subscriptionId: str, token: str):
            key = f"{packageName}:{subscriptionId}:{token}"

            # 检查是否有预设的错误
            if key in self._acknowledge_errors and self._acknowledge_errors[key] is not None:
                raise self._acknowledge_errors[key]

            # 检查是否预设为失败
            if key in self._acknowledge_success and not self._acknowledge_success[key]:
                raise HttpError(MagicMock(status=500), b"{}")

            mock_request = MagicMock()
            mock_request.execute.return_value = {}
            return mock_request

        return acknowledge

    def _create_subscription_cancel(self) -> Callable:
        """创建订阅取消方法"""

        def cancel(packageName: str, subscriptionId: str, token: str):
            key = f"{packageName}:{subscriptionId}:{token}"

            # 检查是否有预设的错误
            if key in self._cancel_errors and self._cancel_errors[key] is not None:
                raise self._cancel_errors[key]

            # 检查是否预设为失败
            if key in self._cancel_success and not self._cancel_success[key]:
                raise HttpError(MagicMock(status=500), b"{}")

            mock_request = MagicMock()
            mock_request.execute.return_value = {}
            return mock_request

        return cancel

    def _create_subscription_defer(self) -> Callable:
        """创建订阅延期方法"""

        def defer(packageName: str, subscriptionId: str, token: str, body: Dict[str, Any]):
            key = f"{packageName}:{subscriptionId}:{token}"

            # 检查是否有预设的错误
            if key in self._defer_errors and self._defer_errors[key] is not None:
                raise self._defer_errors[key]

            # 检查是否预设为失败
            if key in self._defer_success and not self._defer_success[key]:
                raise HttpError(MagicMock(status=500), b"{}")

            mock_request = MagicMock()
            mock_request.execute.return_value = {}
            return mock_request

        return defer

    def _create_edit_insert(self) -> Callable:
        """创建编辑插入方法"""

        def insert(body: Dict[str, Any], packageName: str):
            key = packageName

            # 检查是否有预设的错误
            if key in self._edit_errors and self._edit_errors[key] is not None:
                raise self._edit_errors[key]

            # 生成编辑ID
            self._edit_id_counter += 1
            edit_id = f"edit_{self._edit_id_counter}"

            # 返回预设的响应或默认响应
            if key in self._edit_responses:
                response = self._edit_responses[key]
            else:
                response = {"id": edit_id}

            mock_request = MagicMock()
            mock_request.execute.return_value = response
            return mock_request

        return insert

    def _create_edit_delete(self) -> Callable:
        """创建编辑删除方法"""

        def delete(packageName: str, editId: str):
            mock_request = MagicMock()
            mock_request.execute.return_value = {}
            return mock_request

        return delete

    def _create_track_get(self) -> Callable:
        """创建轨道获取方法"""

        def get(packageName: str, editId: str, track: str):
            key = f"{packageName}:{editId}:{track}"

            # 检查是否有预设的错误
            if key in self._track_errors and self._track_errors[key] is not None:
                raise self._track_errors[key]

            # 返回预设的响应
            if key in self._track_responses:
                response = self._track_responses[key]
            else:
                # 默认响应
                response = {
                    "releases": [
                        {
                            "versionCodes": ["100"],
                            "name": "1.0.0",
                            "status": "completed",
                            "releaseNotes": [{"language": "en-US", "text": "Release notes"}],
                        }
                    ]
                }

            mock_request = MagicMock()
            mock_request.execute.return_value = response
            return mock_request

        return get

    # 设置响应的方法

    def set_subscription_response(
        self, package_name: str, product_id: str, token: str, response: Dict[str, Any]
    ):
        """设置订阅响应"""
        key = f"{package_name}:{product_id}:{token}"
        self._subscription_responses[key] = response

    def set_product_response(
        self, package_name: str, product_id: str, token: str, response: Dict[str, Any]
    ):
        """设置产品响应"""
        key = f"{package_name}:{product_id}:{token}"
        self._product_responses[key] = response

    def set_subscription_error(
        self, package_name: str, product_id: str, token: str, error: Optional[HttpError]
    ):
        """设置订阅错误"""
        key = f"{package_name}:{product_id}:{token}"
        self._subscription_errors[key] = error

    def set_product_error(
        self, package_name: str, product_id: str, token: str, error: Optional[HttpError]
    ):
        """设置产品错误"""
        key = f"{package_name}:{product_id}:{token}"
        self._product_errors[key] = error

    def set_track_response(
        self, package_name: str, edit_id: str, track: str, response: Dict[str, Any]
    ):
        """设置轨道响应"""
        key = f"{package_name}:{edit_id}:{track}"
        self._track_responses[key] = response

    def set_track_error(
        self, package_name: str, edit_id: str, track: str, error: Optional[HttpError]
    ):
        """设置轨道错误"""
        key = f"{package_name}:{edit_id}:{track}"
        self._track_errors[key] = error

    def set_edit_error(self, package_name: str, error: Optional[HttpError]):
        """设置编辑错误"""
        self._edit_errors[package_name] = error

    def set_acknowledge_success(
        self, package_name: str, product_id: str, token: str, success: bool
    ):
        """设置确认订阅成功/失败"""
        key = f"{package_name}:{product_id}:{token}"
        self._acknowledge_success[key] = success

    def set_acknowledge_error(
        self, package_name: str, product_id: str, token: str, error: Optional[HttpError]
    ):
        """设置确认订阅错误"""
        key = f"{package_name}:{product_id}:{token}"
        self._acknowledge_errors[key] = error

    def set_cancel_success(
        self, package_name: str, product_id: str, token: str, success: bool
    ):
        """设置取消订阅成功/失败"""
        key = f"{package_name}:{product_id}:{token}"
        self._cancel_success[key] = success

    def set_cancel_error(
        self, package_name: str, product_id: str, token: str, error: Optional[HttpError]
    ):
        """设置取消订阅错误"""
        key = f"{package_name}:{product_id}:{token}"
        self._cancel_errors[key] = error

    def set_defer_success(
        self, package_name: str, product_id: str, token: str, success: bool
    ):
        """设置延期订阅成功/失败"""
        key = f"{package_name}:{product_id}:{token}"
        self._defer_success[key] = success

    def set_defer_error(
        self, package_name: str, product_id: str, token: str, error: Optional[HttpError]
    ):
        """设置延期订阅错误"""
        key = f"{package_name}:{product_id}:{token}"
        self._defer_errors[key] = error

    @staticmethod
    def create_http_error(status_code: int, message: str = "") -> HttpError:
        """创建 HttpError 异常"""
        resp = MagicMock()
        resp.status = status_code
        return HttpError(resp, message.encode() if message else b"{}")

