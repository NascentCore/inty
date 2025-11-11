package com.ai.intellimate.utils

import ai.sxwl.android.data.billing.BillingErrorCode
import ai.sxwl.android.data.billing.BillingEvent
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import android.app.Activity
import android.content.Context
import com.ai.intellimate.R
import com.google.android.gms.common.GoogleApiAvailability

/** Billing 错误处理工具类 - 负责将错误码转换为用户友好的 toast 提示
 *
 * 职责：
 * - 将 BillingErrorCode 映射到 strings.xml 中的错误消息
 * - 显示 toast 提示
 * - 处理 Google Play 服务的 Dialog
 */
object BillingErrorHandler {

    /** 根据错误码获取错误消息字符串资源 ID */
    private fun getErrorMessageResId(errorCode: BillingErrorCode): Int {
        return when (errorCode) {
            // 购买相关错误
            BillingErrorCode.PURCHASES_EMPTY -> R.string.billing_error_purchases_empty
            BillingErrorCode.ITEM_ALREADY_OWNED -> R.string.billing_error_item_already_owned
            BillingErrorCode.ITEM_NOT_OWNED -> R.string.billing_error_item_not_owned
            BillingErrorCode.ITEM_UNAVAILABLE -> R.string.billing_error_item_unavailable
            BillingErrorCode.PURCHASE_FAILED -> R.string.billing_error_purchase_failed
            BillingErrorCode.PURCHASE_ACKNOWLEDGMENT_FAILED -> R.string.billing_error_purchase_acknowledgment_failed

            // 订阅验证相关错误
            BillingErrorCode.SUBSCRIPTION_VERIFICATION_FAILED -> R.string.billing_error_subscription_verification_failed
            BillingErrorCode.SUBSCRIPTION_VERIFICATION_EXCEPTION -> R.string.billing_error_subscription_verification_exception

            // Google Play 服务相关错误
            BillingErrorCode.GOOGLE_PLAY_SERVICE_UPDATE_REQUIRED -> R.string.billing_error_google_play_service_update_required
            BillingErrorCode.GOOGLE_PLAY_SERVICE_DISABLED -> R.string.billing_error_google_play_service_disabled
            BillingErrorCode.GOOGLE_PLAY_SERVICE_MISSING -> R.string.billing_error_google_play_service_missing
            BillingErrorCode.GOOGLE_PLAY_SERVICE_INVALID -> R.string.billing_error_google_play_service_invalid
            BillingErrorCode.GOOGLE_PLAY_SERVICE_UNAVAILABLE -> R.string.billing_error_google_play_service_unavailable

            // 计费功能相关错误
            BillingErrorCode.BILLING_NOT_SUPPORTED -> R.string.billing_error_billing_not_supported
            BillingErrorCode.BILLING_FEATURE_NOT_SUPPORTED -> R.string.billing_error_billing_feature_not_supported

            // 服务相关错误
            BillingErrorCode.SERVICE_UNAVAILABLE -> R.string.billing_error_service_unavailable
            BillingErrorCode.NETWORK_ERROR -> R.string.billing_error_network_error
            BillingErrorCode.DEVELOPER_ERROR -> R.string.billing_error_developer_error

            // 商品查询相关错误
            BillingErrorCode.PRODUCT_DETAILS_NOT_FOUND -> R.string.billing_error_product_details_not_found
            BillingErrorCode.PRODUCT_DETAILS_QUERY_FAILED -> R.string.billing_error_product_details_query_failed

            // 前置检查错误
            BillingErrorCode.PURCHASE_PRECONDITIONS_CHECK_FAILED -> R.string.billing_error_purchase_preconditions_check_failed
            BillingErrorCode.BILLING_SUPPORT_CHECK_ERROR -> R.string.billing_error_billing_support_check_error

            // 未知错误
            BillingErrorCode.UNKNOWN_ERROR -> R.string.billing_error_unknown_error
        }
    }

    /** 处理需要显示 toast 的错误事件 */
    fun handleShowError(event: BillingEvent.ShowError, context: Context) {
        try {
            val messageResId = getErrorMessageResId(event.errorCode)
            val message = context.getString(messageResId)

            // 如果有详细消息且错误消息支持格式化参数，则使用格式化字符串
            val finalMessage = if (event.detailMessage != null && message.contains("%s")) {
                try {
                    message.format(event.detailMessage)
                } catch (e: Exception) {
                    // 如果格式化失败，使用原始消息
                    "$message: ${event.detailMessage}"
                }
            } else {
                message
            }

            // 只对用户主动操作显示 toast，后台自动操作只记录 log
            if (event.isUserInitiated) {
                ToastUtils.showShort(finalMessage)
                LogUtils.d("BillingErrorHandler - 显示错误提示: $finalMessage")
            } else {
                LogUtils.d("BillingErrorHandler - 后台自动操作错误（不显示 toast）: $finalMessage")
            }
        } catch (e: Exception) {
            LogUtils.e("BillingErrorHandler - 处理错误事件失败: ${e.message}")
            // 只对用户主动操作显示 toast
            if (event.isUserInitiated) {
                val fallbackMessage = event.detailMessage
                    ?: context.getString(R.string.billing_error_fallback_generic)
                ToastUtils.showShort(fallbackMessage)
            } else {
                LogUtils.d("BillingErrorHandler - 后台自动操作错误（不显示 toast）: ${event.detailMessage}")
            }
        }
    }

    /** 处理购买失败事件 */
    fun handlePurchaseFailed(event: BillingEvent.PurchaseFailed, context: Context) {
        try {
            val messageResId = getErrorMessageResId(event.errorCode)
            val message = context.getString(messageResId)

            val finalMessage = if (event.detailMessage != null && message.contains("%s")) {
                try {
                    message.format(event.detailMessage)
                } catch (e: Exception) {
                    "$message: ${event.detailMessage}"
                }
            } else {
                message
            }

            // 只对用户主动操作显示 toast，后台自动操作只记录 log
            if (event.isUserInitiated) {
                ToastUtils.showShort(finalMessage)
                LogUtils.d("BillingErrorHandler - 购买失败: $finalMessage")
            } else {
                LogUtils.d("BillingErrorHandler - 后台自动操作购买失败（不显示 toast）: $finalMessage")
            }
        } catch (e: Exception) {
            LogUtils.e("BillingErrorHandler - 处理购买失败事件失败: ${e.message}")
            // 只对用户主动操作显示 toast
            if (event.isUserInitiated) {
                val fallbackMessage = event.detailMessage
                    ?: context.getString(R.string.billing_error_fallback_purchase)
                ToastUtils.showShort(fallbackMessage)
            } else {
                LogUtils.d("BillingErrorHandler - 后台自动操作购买失败（不显示 toast）: ${event.detailMessage}")
            }
        }
    }

    /** 处理商品详情查询失败事件 */
    fun handleSkuDetailsQueryFailed(event: BillingEvent.SkuDetailsQueryFailed, context: Context) {
        try {
            val messageResId = getErrorMessageResId(event.errorCode)
            val message = context.getString(messageResId)

            val finalMessage = if (event.detailMessage != null && message.contains("%s")) {
                try {
                    message.format(event.detailMessage)
                } catch (e: Exception) {
                    "$message: ${event.detailMessage}"
                }
            } else {
                message
            }

            // 只对用户主动操作显示 toast，后台自动操作只记录 log
            if (event.isUserInitiated) {
                ToastUtils.showShort(finalMessage)
                LogUtils.d("BillingErrorHandler - 商品查询失败: $finalMessage")
            } else {
                LogUtils.d("BillingErrorHandler - 后台自动操作商品查询失败（不显示 toast）: $finalMessage")
            }
        } catch (e: Exception) {
            LogUtils.e("BillingErrorHandler - 处理商品查询失败事件失败: ${e.message}")
            // 只对用户主动操作显示 toast
            if (event.isUserInitiated) {
                val fallbackMessage = event.detailMessage
                    ?: context.getString(R.string.billing_error_fallback_product_details)
                ToastUtils.showShort(fallbackMessage)
            } else {
                LogUtils.d("BillingErrorHandler - 后台自动操作商品查询失败（不显示 toast）: ${event.detailMessage}")
            }
        }
    }

    /** 处理 Google Play 服务错误 - 显示系统 Dialog */
    fun handleGooglePlayServiceError(
        event: BillingEvent.GooglePlayServiceError,
        activity: Activity
    ) {
        try {
            // 只对用户主动操作显示 Dialog/toast，后台自动操作只记录 log
            if (!event.isUserInitiated) {
                LogUtils.d("BillingErrorHandler - 后台自动操作 Google Play 服务错误（不显示 Dialog）: ${event.errorCode}")
                return
            }

            when (event.errorCode) {
                BillingErrorCode.GOOGLE_PLAY_SERVICE_UPDATE_REQUIRED -> {
                    // 显示 Google Play Services 更新 Dialog
                    val googleApiAvailability = GoogleApiAvailability.getInstance()
                    googleApiAvailability.getErrorDialog(
                        activity,
                        event.connectionResult,
                        event.requestCode
                    )?.show()
                    LogUtils.d("BillingErrorHandler - 显示 Google Play 服务更新 Dialog")
                }

                else -> {
                    // 其他 Google Play 服务错误，显示 toast
                    val context = activity.applicationContext
                    val messageResId = getErrorMessageResId(event.errorCode)
                    val message = context.getString(messageResId)
                    ToastUtils.showShort(message)
                    LogUtils.d("BillingErrorHandler - Google Play 服务错误: $message")
                }
            }
        } catch (e: Exception) {
            LogUtils.e("BillingErrorHandler - 处理 Google Play 服务错误失败: ${e.message}")
            // 只对用户主动操作显示 toast
            if (event.isUserInitiated) {
                val context = activity.applicationContext
                ToastUtils.showShort(context.getString(R.string.billing_error_fallback_google_play_service))
            } else {
                LogUtils.d("BillingErrorHandler - 后台自动操作 Google Play 服务错误（不显示 toast）")
            }
        }
    }

    /** 处理初始化失败事件 */
    fun handleInitializationFailed(event: BillingEvent.InitializationFailed, context: Context) {
        try {
            val messageResId = getErrorMessageResId(event.errorCode)
            val message = context.getString(messageResId)
            // 初始化失败是后台自动操作，只记录 log，不显示 toast
            LogUtils.d("BillingErrorHandler - 初始化失败（不显示 toast）: $message, reason: ${event.reason}")
        } catch (e: Exception) {
            LogUtils.e("BillingErrorHandler - 处理初始化失败事件失败: ${e.message}")
            // 初始化失败是后台自动操作，不显示 toast
            LogUtils.d("BillingErrorHandler - 初始化失败（不显示 toast）: ${event.reason}")
        }
    }

    /** 统一处理 BillingEvent - 根据事件类型分发到对应的处理方法 */
    fun handleBillingEvent(event: BillingEvent, context: Context, activity: Activity? = null) {
        when (event) {
            is BillingEvent.ShowError -> {
                handleShowError(event, context)
            }

            is BillingEvent.PurchaseFailed -> {
                handlePurchaseFailed(event, context)
            }

            is BillingEvent.SkuDetailsQueryFailed -> {
                handleSkuDetailsQueryFailed(event, context)
            }

            is BillingEvent.GooglePlayServiceError -> {
                activity?.let {
                    handleGooglePlayServiceError(event, it)
                } ?: run {
                    LogUtils.w("BillingErrorHandler - GooglePlayServiceError 需要 Activity，但未提供")
                    handleShowError(
                        BillingEvent.ShowError(
                            event.errorCode,
                            isUserInitiated = event.isUserInitiated
                        ),
                        context
                    )
                }
            }

            is BillingEvent.InitializationFailed -> {
                handleInitializationFailed(event, context)
            }

            else -> {
                // 其他事件不需要 UI 处理
                LogUtils.d("BillingErrorHandler - 忽略不需要 UI 处理的事件: ${event::class.simpleName}")
            }
        }
    }
}
