from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from loguru import logger

from app.utils.config import GooglePlayConfig
from app.schemas.version import VersionReminderAction


class GooglePlayService:
    """Google Play Developer API服务"""

    def __init__(self, android_publisher_service: Resource, config: GooglePlayConfig):
        """初始化Google Play服务"""
        self.service = android_publisher_service
        self.config = config
        self.package_name = config.package_name

    def verify_subscription_purchase(
        self, product_id: str, purchase_token: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        验证订阅购买

        Args:
            product_id: 产品ID
            purchase_token: 购买令牌

        Returns:
            Tuple[bool, Dict]: (是否有效, 购买信息)
        """
        try:
            # 调用Google Play API验证订阅
            result = (
                self.service.purchases()
                .subscriptions()
                .get(
                    packageName=self.package_name,
                    subscriptionId=product_id,
                    token=purchase_token,
                )
                .execute()
            )

            logger.info(
                f"订阅验证成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}..."
            )

            # 解析响应
            purchase_info = self._parse_subscription_purchase(result)

            # 判断订阅是否有效
            is_valid = self._is_subscription_valid(purchase_info)

            return is_valid, purchase_info

        except HttpError as e:
            # HttpError 400 通常是产品ID不匹配的预期情况，降级为 DEBUG
            # 其他错误（401, 403, 500等）保持 ERROR 级别
            status_code = (
                e.resp.status
                if hasattr(e, "resp") and hasattr(e.resp, "status")
                else None
            )
            if status_code == 400:
                logger.debug(
                    f"Google Play API调用失败 (产品ID不匹配): {e}, product_id: {product_id}, purchase_token: {purchase_token[:10]}..."
                )
            else:
                logger.error(
                    f"Google Play API调用失败: {e}, product_id: {product_id}, purchase_token: {purchase_token[:10]}..., status_code: {status_code}"
                )
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"订阅验证失败: {str(e)}")
            return False, {"error": str(e)}

    def verify_product_purchase(
        self, product_id: str, purchase_token: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        验证一次性产品购买

        Args:
            product_id: 产品ID
            purchase_token: 购买令牌

        Returns:
            Tuple[bool, Dict]: (是否有效, 购买信息)
        """
        try:
            # 调用Google Play API验证一次性产品购买
            result = (
                self.service.purchases()
                .products()
                .get(
                    packageName=self.package_name,
                    productId=product_id,
                    token=purchase_token,
                )
                .execute()
            )

            logger.info(
                f"产品购买验证成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}..."
            )

            # 解析响应
            purchase_info = self._parse_product_purchase(result)

            # 判断购买是否有效
            is_valid = self._is_product_purchase_valid(purchase_info)

            return is_valid, purchase_info

        except HttpError as e:
            logger.error(f"Google Play API调用失败: {e}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"产品购买验证失败: {str(e)}")
            return False, {"error": str(e)}

    def acknowledge_subscription(self, product_id: str, purchase_token: str) -> bool:
        """
        确认订阅购买

        Args:
            product_id: 产品ID
            purchase_token: 购买令牌

        Returns:
            bool: 是否成功
        """
        try:
            self.service.purchases().subscriptions().acknowledge(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token,
            ).execute()

            logger.info(
                f"订阅确认成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}..."
            )
            return True

        except HttpError as e:
            logger.error(f"订阅确认失败: {e}")
            return False
        except Exception as e:
            logger.error(f"订阅确认失败: {str(e)}")
            return False

    def cancel_subscription(self, product_id: str, purchase_token: str) -> bool:
        """
        取消订阅

        Args:
            product_id: 产品ID
            purchase_token: 购买令牌

        Returns:
            bool: 是否成功
        """
        try:
            self.service.purchases().subscriptions().cancel(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token,
            ).execute()

            logger.info(
                f"订阅取消成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}..."
            )
            return True

        except HttpError as e:
            logger.error(f"订阅取消失败: {e}")
            return False
        except Exception as e:
            logger.error(f"订阅取消失败: {str(e)}")
            return False

    def defer_subscription(
        self, product_id: str, purchase_token: str, expiry_time_millis: int
    ) -> bool:
        """
        延期订阅

        Args:
            product_id: 产品ID
            purchase_token: 购买令牌
            expiry_time_millis: 新的到期时间（毫秒）

        Returns:
            bool: 是否成功
        """
        try:
            body = {
                "deferralInfo": {"expectedExpiryTimeMillis": str(expiry_time_millis)}
            }

            self.service.purchases().subscriptions().defer(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token,
                body=body,
            ).execute()

            logger.info(
                f"订阅延期成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}..."
            )
            return True

        except HttpError as e:
            logger.error(f"订阅延期失败: {e}")
            return False
        except Exception as e:
            logger.error(f"订阅延期失败: {str(e)}")
            return False

    def _parse_subscription_purchase(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析订阅购买响应"""
        try:
            purchase_info = {
                "start_time": self._millis_to_datetime(result.get("startTimeMillis")),
                "expiry_time": self._millis_to_datetime(result.get("expiryTimeMillis")),
                "auto_renewing": result.get("autoRenewing", False),
                "price_amount_micros": result.get("priceAmountMicros", 0),
                "price_currency_code": result.get("priceCurrencyCode", "USD"),
                "payment_state": result.get("paymentState", 0),
                "cancel_reason": result.get("cancelReason"),
                "user_cancellation_time": self._millis_to_datetime(
                    result.get("userCancellationTimeMillis")
                ),
                "order_id": result.get("orderId"),
                "linked_purchase_token": result.get("linkedPurchaseToken"),
                "purchase_type": result.get("purchaseType"),
                "acknowledgement_state": result.get("acknowledgementState", 0),
                "kind": result.get("kind"),
                "developer_payload": result.get("developerPayload"),
                "profile_name": result.get("profileName"),
                "email_address": result.get("emailAddress"),
                "given_name": result.get("givenName"),
                "family_name": result.get("familyName"),
                "profile_id": result.get("profileId"),
                # ObfuscatedAccountId 相关字段（如果 app 端设置了 setObfuscatedAccountId）
                # 注意：字段名称可能因 API 版本而异，需要根据实际响应调整
                "obfuscated_external_account_id": result.get(
                    "obfuscatedExternalAccountId"
                )
                or result.get("obfuscatedAccountId"),
                "obfuscated_external_profile_id": result.get(
                    "obfuscatedExternalProfileId"
                )
                or result.get("obfuscatedProfileId"),
                "raw_response": result,
            }

            return purchase_info

        except Exception as e:
            logger.error(f"解析订阅购买响应失败: {str(e)}")
            return {"error": str(e), "raw_response": result}

    def _parse_product_purchase(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析一次性产品购买响应"""
        try:
            purchase_info = {
                "purchase_time": self._millis_to_datetime(
                    result.get("purchaseTimeMillis")
                ),
                "purchase_state": result.get("purchaseState", 0),
                "consumption_state": result.get("consumptionState", 0),
                "developer_payload": result.get("developerPayload"),
                "order_id": result.get("orderId"),
                "purchase_type": result.get("purchaseType"),
                "acknowledgement_state": result.get("acknowledgementState", 0),
                "kind": result.get("kind"),
                "region_code": result.get("regionCode"),
                "raw_response": result,
            }

            return purchase_info

        except Exception as e:
            logger.error(f"解析产品购买响应失败: {str(e)}")
            return {"error": str(e), "raw_response": result}

    def _is_subscription_valid(self, purchase_info: Dict[str, Any]) -> bool:
        """判断订阅是否有效"""
        try:
            # 检查是否有错误
            if "error" in purchase_info:
                return False

            # 检查支付状态 (0: 待支付, 1: 已支付, 2: 免费试用, 3: 待延期升级)
            payment_state = purchase_info.get("payment_state", 0)
            if payment_state not in [1, 2, 3]:
                return False

            # 检查是否过期
            expiry_time = purchase_info.get("expiry_time")
            if expiry_time and expiry_time < datetime.now(timezone.utc):
                return False

            # 检查是否已取消且不在宽限期内
            cancel_reason = purchase_info.get("cancel_reason")
            if cancel_reason is not None:
                # 如果有取消原因，检查是否在宽限期内
                user_cancellation_time = purchase_info.get("user_cancellation_time")
                if user_cancellation_time and expiry_time:
                    # 如果当前时间超过了取消时间但还在到期时间内，说明在宽限期
                    now = datetime.now(timezone.utc)
                    if now > user_cancellation_time and now < expiry_time:
                        return True
                return False

            return True

        except Exception as e:
            logger.error(f"判断订阅有效性失败: {str(e)}")
            return False

    def _is_product_purchase_valid(self, purchase_info: Dict[str, Any]) -> bool:
        """判断一次性产品购买是否有效"""
        try:
            # 检查是否有错误
            if "error" in purchase_info:
                return False

            # 检查购买状态 (0: 已购买, 1: 已取消, 2: 待支付)
            purchase_state = purchase_info.get("purchase_state", 0)
            if purchase_state != 0:
                return False

            # 检查消费状态 (0: 未消费, 1: 已消费)
            consumption_state = purchase_info.get("consumption_state", 0)
            if consumption_state != 0:
                return False

            # 检查确认状态 (0: 未确认, 1: 已确认)
            acknowledgement_state = purchase_info.get("acknowledgement_state", 0)
            if acknowledgement_state != 1:
                return False

            return True

        except Exception as e:
            logger.error(f"判断产品购买有效性失败: {str(e)}")
            return False

    def _millis_to_datetime(self, millis: Optional[str]) -> Optional[datetime]:
        """将毫秒时间戳转换为datetime对象"""
        if not millis:
            return None

        try:
            timestamp = int(millis) / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, TypeError):
            return None

    def get_subscription_details(
        self, product_id: str, purchase_token: str
    ) -> Dict[str, Any]:
        """
        获取订阅详细信息

        Args:
            product_id: 产品ID
            purchase_token: 购买令牌

        Returns:
            Dict: 订阅详细信息
        """
        try:
            result = (
                self.service.purchases()
                .subscriptions()
                .get(
                    packageName=self.package_name,
                    subscriptionId=product_id,
                    token=purchase_token,
                )
                .execute()
            )

            return self._parse_subscription_purchase(result)

        except Exception as e:
            logger.error(f"获取订阅详细信息失败: {str(e)}")
            return {"error": str(e)}

    def get_app_version_info(self) -> Dict[str, Any]:
        """
        获取应用版本信息

        Returns:
            Dict: 包含最新版本信息的字典
        """
        # 如果配置了覆盖版本代码，直接使用配置值，跳过 Google Play API 调用
        if self.config.current_version_code > 0:
            logger.debug(
                f"使用配置的版本代码: {self.config.current_version_code}（跳过 Google Play API）"
            )
            return {
                "version_code": self.config.current_version_code,
                "version_name": str(self.config.current_version_code),
                "status": "completed",
                "release_notes": None,
                "user_fraction": None,
                "country_targeting": None,
                "track": "config_override",
            }

        try:
            # 获取应用的编辑信息
            edit_request = self.service.edits().insert(
                body={}, packageName=self.package_name
            )
            edit_result = edit_request.execute()
            edit_id = edit_result["id"]

            try:
                # 尝试从配置的轨道获取版本信息
                primary_track = self.config.release_track
                fallback_tracks = self.config.fallback_tracks

                # 构建要尝试的轨道列表
                tracks_to_try = [primary_track]
                if fallback_tracks:
                    tracks_to_try.extend(
                        [track for track in fallback_tracks if track != primary_track]
                    )

                logger.debug(f"尝试从轨道获取版本信息，轨道顺序: {tracks_to_try}")

                for track_name in tracks_to_try:
                    try:
                        logger.debug(f"正在查询轨道: {track_name}")
                        track_result = (
                            self.service.edits()
                            .tracks()
                            .get(
                                packageName=self.package_name,
                                editId=edit_id,
                                track=track_name,
                            )
                            .execute()
                        )

                        if track_result.get("releases"):
                            # 获取最新版本（releases列表按时间倒序排列）
                            latest_release = track_result["releases"][0]

                            version_info = {
                                "version_code": latest_release.get("versionCodes", [0])[
                                    0
                                ],
                                "version_name": latest_release.get("name", ""),
                                "status": latest_release.get("status", ""),
                                "release_notes": self._extract_release_notes(
                                    latest_release
                                ),
                                "user_fraction": latest_release.get("userFraction"),
                                "country_targeting": latest_release.get(
                                    "countryTargeting"
                                ),
                                "track": track_name,  # 添加轨道信息
                            }

                            logger.debug(
                                f"从轨道 {track_name} 获取应用版本信息成功: {version_info}"
                            )
                            return version_info
                        else:
                            logger.debug(f"轨道 {track_name} 没有找到版本信息")
                            continue

                    except HttpError as track_error:
                        logger.warning(f"查询轨道 {track_name} 失败: {track_error}")
                        continue

                # 所有轨道都没有找到版本信息
                logger.warning(f"所有轨道都未找到版本信息: {tracks_to_try}")
                return {"error": "No releases found in any track"}

            finally:
                # 删除编辑会话
                try:
                    self.service.edits().delete(
                        packageName=self.package_name, editId=edit_id
                    ).execute()
                except Exception as cleanup_error:
                    logger.warning(f"清理编辑会话失败: {cleanup_error}")

        except HttpError as e:
            logger.error(f"Google Play API调用失败 - 获取版本信息: {e}")
            return {"error": f"API Error: {e}"}
        except Exception as e:
            logger.error(f"获取应用版本信息失败: {str(e)}")
            return {"error": str(e)}

    def _extract_release_notes(self, release: Dict[str, Any]) -> Optional[str]:
        """提取发布说明"""
        try:
            release_notes = release.get("releaseNotes", [])
            if release_notes:
                # 优先返回中文版本，如果没有则返回第一个可用版本
                for note in release_notes:
                    if note.get("language") in ["zh-CN", "zh"]:
                        return note.get("text", "")

                # 如果没有中文版本，返回第一个
                return release_notes[0].get("text", "")

            return None
        except Exception as e:
            logger.warning(f"提取发布说明失败: {e}")
            return None

    def check_version_requirement(self, client_version_code: int) -> Dict[str, Any]:
        """
        检查版本更新要求

        Args:
            client_version_code: 客户端版本代码

        Returns:
            Dict: 版本检查结果
        """
        download_url_value = (
            f"https://play.google.com/store/apps/details?id={self.package_name}"
        )
        result = {
            "current_version": str(client_version_code),
            "latest_version": "unknown",
            "latest_version_code": 0,
            "minimum_version": str(self.config.min_supported_version) or "0",
            "download_url": download_url_value,
            "changelog": None,
            "update_required": False,
            "force_update": False,
            "reminder_action": VersionReminderAction.NONE,
        }
        # 如果版本检查被禁用
        if not self.config.enable_version_check:
            logger.debug("版本检查被禁用，跳过检查，返回默认值")
            return result | {
                "update_required": False,
                "force_update": False,
                "message": "Version check disabled",
                "reminder_action": VersionReminderAction.NONE,
            }

        version_info = self.get_app_version_info()
        logger.debug(f"获取版本信息: {version_info}")

        if "error" in version_info:
            logger.warning(f"无法获取版本信息，跳过版本检查: {version_info['error']}")
            return result | {
                "error": version_info["error"],
                "message": "Unable to fetch version info",
                "reminder_action": VersionReminderAction.NONE,
            }

        latest_version_code_raw = version_info.get("version_code", 0)

        # 将版本代码转换为整数
        try:
            latest_version_code = int(latest_version_code_raw)
        except (ValueError, TypeError):
            logger.warning(f"最新版本代码无效: {latest_version_code_raw}, 使用默认值 0")
            latest_version_code = 0

        version_code_gap = latest_version_code - client_version_code
        reminder_action = VersionReminderAction.NONE
        # 按阈值从大到小检查，找到第一个匹配的阈值即返回对应的动作
        for gap_threshold, action in [
            (
                self.config.force_update_version_code_gap,
                VersionReminderAction.BLOCK_ACCESS,
            ),
            (
                self.config.popup_reminder_version_code_gap,
                VersionReminderAction.POP_UP_REMINDER,
            ),
            (
                self.config.settings_reminder_version_code_gap,
                VersionReminderAction.SETTINGS_REMINDER,
            ),
        ]:
            if version_code_gap >= gap_threshold:
                reminder_action = action
                break

        # 获取版本信息用于返回
        latest_version_name = version_info.get("version_name", "")
        changelog_value = version_info.get("release_notes")

        result = result | {
            "latest_version": latest_version_name or str(latest_version_code),
            "latest_version_code": latest_version_code,
            "changelog": changelog_value,
            "update_required": reminder_action != VersionReminderAction.NONE,
            "force_update": reminder_action == VersionReminderAction.BLOCK_ACCESS,
            "message": (
                "New version available"
                if reminder_action != VersionReminderAction.NONE
                else "App is up to date"
            ),
            "reminder_action": reminder_action,
        }
        logger.debug(f"版本检查结果: {result}")
        return result
