import json
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings

logger = logging.getLogger(__name__)


class GooglePlayService:
    """Google Play Developer API服务"""
    
    def __init__(self):
        """初始化Google Play服务"""
        self.service = None
        self.package_name = settings.google_play.package_name
        self._initialize_service()
    
    def _initialize_service(self):
        """初始化Google Play Developer API服务"""
        try:
            # 获取服务账号凭据
            service_account_key = settings.google_play.service_account_key
            
            # 检查是否为文件路径还是JSON字符串
            if service_account_key.endswith('.json'):
                # 如果是文件路径，读取文件内容
                from pathlib import Path
                key_path = Path(service_account_key)
                if not key_path.exists():
                    raise FileNotFoundError(f"服务账号密钥文件不存在: {service_account_key}")
                    
                with open(key_path, 'r') as f:
                    service_account_info = json.load(f)
            else:
                # 如果是JSON字符串，直接解析
                service_account_info = json.loads(service_account_key)
            
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/androidpublisher']
            )
            
            self.service = build('androidpublisher', 'v3', credentials=credentials)
            logger.info("Google Play Developer API服务初始化成功")
            
        except Exception as e:
            logger.error(f"Google Play Developer API服务初始化失败: {str(e)}")
            raise
    
    def verify_subscription_purchase(self, product_id: str, purchase_token: str) -> Tuple[bool, Dict[str, Any]]:
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
            result = self.service.purchases().subscriptions().get(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token
            ).execute()
            
            logger.info(f"订阅验证成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}...")
            
            # 解析响应
            purchase_info = self._parse_subscription_purchase(result)
            
            # 判断订阅是否有效
            is_valid = self._is_subscription_valid(purchase_info)
            
            return is_valid, purchase_info
            
        except HttpError as e:
            logger.error(f"Google Play API调用失败: {e}, product_id: {product_id}, purchase_token: {purchase_token}")
            return False, {"error": str(e)}
        except Exception as e:
            logger.error(f"订阅验证失败: {str(e)}")
            return False, {"error": str(e)}
    
    def verify_product_purchase(self, product_id: str, purchase_token: str) -> Tuple[bool, Dict[str, Any]]:
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
            result = self.service.purchases().products().get(
                packageName=self.package_name,
                productId=product_id,
                token=purchase_token
            ).execute()
            
            logger.info(f"产品购买验证成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}...")
            
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
                token=purchase_token
            ).execute()
            
            logger.info(f"订阅确认成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}...")
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
                token=purchase_token
            ).execute()
            
            logger.info(f"订阅取消成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}...")
            return True
            
        except HttpError as e:
            logger.error(f"订阅取消失败: {e}")
            return False
        except Exception as e:
            logger.error(f"订阅取消失败: {str(e)}")
            return False
    
    def defer_subscription(self, product_id: str, purchase_token: str, expiry_time_millis: int) -> bool:
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
                "deferralInfo": {
                    "expectedExpiryTimeMillis": str(expiry_time_millis)
                }
            }
            
            self.service.purchases().subscriptions().defer(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token,
                body=body
            ).execute()
            
            logger.info(f"订阅延期成功 - 产品ID: {product_id}, 令牌: {purchase_token[:10]}...")
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
                "user_cancellation_time": self._millis_to_datetime(result.get("userCancellationTimeMillis")),
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
                "raw_response": result
            }
            
            return purchase_info
            
        except Exception as e:
            logger.error(f"解析订阅购买响应失败: {str(e)}")
            return {"error": str(e), "raw_response": result}
    
    def _parse_product_purchase(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """解析一次性产品购买响应"""
        try:
            purchase_info = {
                "purchase_time": self._millis_to_datetime(result.get("purchaseTimeMillis")),
                "purchase_state": result.get("purchaseState", 0),
                "consumption_state": result.get("consumptionState", 0),
                "developer_payload": result.get("developerPayload"),
                "order_id": result.get("orderId"),
                "purchase_type": result.get("purchaseType"),
                "acknowledgement_state": result.get("acknowledgementState", 0),
                "kind": result.get("kind"),
                "region_code": result.get("regionCode"),
                "raw_response": result
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
    
    def get_subscription_details(self, product_id: str, purchase_token: str) -> Dict[str, Any]:
        """
        获取订阅详细信息
        
        Args:
            product_id: 产品ID
            purchase_token: 购买令牌
            
        Returns:
            Dict: 订阅详细信息
        """
        try:
            result = self.service.purchases().subscriptions().get(
                packageName=self.package_name,
                subscriptionId=product_id,
                token=purchase_token
            ).execute()
            
            return self._parse_subscription_purchase(result)
            
        except Exception as e:
            logger.error(f"获取订阅详细信息失败: {str(e)}")
            return {"error": str(e)}


# 全局实例
google_play_service = GooglePlayService() 