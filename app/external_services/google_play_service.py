from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from loguru import logger

from app.core.config import global_config_loaded_from_config_yaml


class GooglePlayService:
    """Google Play Developer API服务"""

    def __init__(self, android_publisher_service: Resource):
        """初始化Google Play服务"""
        self.service = android_publisher_service
        self.package_name = (
            global_config_loaded_from_config_yaml.google_play.package_name
        )

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
            logger.error(
                f"Google Play API调用失败: {e}, product_id: {product_id}, purchase_token: {purchase_token}"
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
        try:
            # 获取应用的编辑信息
            edit_request = self.service.edits().insert(
                body={}, packageName=self.package_name
            )
            edit_result = edit_request.execute()
            edit_id = edit_result["id"]

            try:
                # 尝试从配置的轨道获取版本信息
                primary_track = (
                    global_config_loaded_from_config_yaml.google_play.release_track
                )
                fallback_tracks = (
                    global_config_loaded_from_config_yaml.google_play.fallback_tracks
                )

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
        try:
            # 如果版本检查被禁用
            if (
                not global_config_loaded_from_config_yaml.google_play.enable_version_check
            ):
                return {
                    "update_required": False,
                    "force_update": False,
                    "message": "Version check disabled",
                }

            # 获取最新版本信息
            version_info = self.get_app_version_info()

            if "error" in version_info:
                logger.warning(
                    f"无法获取版本信息，跳过版本检查: {version_info['error']}"
                )
                return {
                    "update_required": False,
                    "force_update": False,
                    "message": "Unable to fetch version info",
                    "error": version_info["error"],
                }

            latest_version_name = version_info.get("version_name", "")
            latest_version_code = version_info.get("version_code", 0)

            # 版本比较
            update_required = self._compare_versions(
                client_version_code, latest_version_code
            )

            # 强制更新检查：扩展多种检查条件
            force_update_reasons = []

            # 1. 检查是否低于最低支持版本
            try:
                min_supported_version_code = int(
                    global_config_loaded_from_config_yaml.google_play.min_supported_version
                )
            except (ValueError, TypeError):
                logger.warning(
                    f"最低支持版本配置无效: {global_config_loaded_from_config_yaml.google_play.min_supported_version}, 使用默认值 1"
                )
                min_supported_version_code = 1

            if client_version_code < min_supported_version_code:
                reason = f"Version code below minimum supported version: {client_version_code} < {min_supported_version_code}"
                force_update_reasons.append(reason)
                logger.info(f"最低版本检查触发强制更新: {reason}")

            force_update = len(force_update_reasons) > 0

            result = {
                "current_version": str(client_version_code),
                "latest_version": latest_version_name,
                "latest_version_code": latest_version_code,
                "update_required": update_required,
                "force_update": force_update,
                "minimum_version": str(min_supported_version_code),
                "changelog": version_info.get("release_notes"),
                "download_url": f"https://play.google.com/store/apps/details?id={self.package_name}",
            }

            # 添加详细的更新原因
            if force_update:
                result["force_update_reasons"] = force_update_reasons
                result["message"] = (
                    f"Force update required: {'; '.join(force_update_reasons)}"
                )
            elif update_required:
                result["message"] = "New version available"
            else:
                result["message"] = "App is up to date"

            # 详细日志记录
            log_msg = (
                f"版本检查完成: 客户端={client_version_code}, 最新={latest_version_code}, "
                f"最低支持={min_supported_version_code}, "
                f"需要更新={update_required}, 强制更新={force_update}"
            )

            if force_update_reasons:
                log_msg += f" (强制更新原因: {'; '.join(force_update_reasons)})"

            logger.info(log_msg)
            return result

        except Exception as e:
            logger.error(f"版本检查失败: {str(e)}")
            return {
                "update_required": False,
                "force_update": False,
                "message": "Version check failed",
                "error": str(e),
            }

    def _compare_versions(self, version_code1, version_code2) -> bool:
        """
        比较版本号，直接比较versionCode，判断version_code1是否小于version_code2

        Args:
            version_code1: 版本代码1 (客户端versionCode)
            version_code2: 版本代码2 (服务端versionCode)

        Returns:
            bool: version_code1 < version_code2 时返回True
        """
        try:
            # 直接比较版本代码
            client_code = int(version_code1)
            server_code = int(version_code2)

            logger.debug(f"版本代码比较: {client_code} vs {server_code}")

            return client_code < server_code

        except Exception as e:
            logger.warning(f"版本代码比较失败，将客户端版本视为需要更新: {e}")
            return True  # 如果比较失败，保守起见要求更新
