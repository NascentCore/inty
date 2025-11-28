package com.ai.intellimate.settings

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.billing.VipStatus
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import androidx.compose.runtime.Immutable
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.R
import com.ai.intellimate.utils.HttpErrorHandler
import com.ai.intellimate.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException

/** 设置页面统一状态 */
@Immutable
data class SettingState(
    val userId: String = "",
    val userEmail: String = "",
    val hasAppUpdateTips: Boolean = false,
    val vipStatus: VipStatus = VipStatus(false),
    val dialogState: DialogState = DialogState(),
) {
    val isVipSubscribed: Boolean
        get() = vipStatus.isSubscribed
}

/** 设置页面 ViewModel */
class SettingViewModel : BaseVM() {

    // 统一状态，合并所有数据源
    private val _state =
        MutableStateFlow(
            SettingState(
                userId = IntySetting.getCurUserID(),
                userEmail = UserProfileManager.getUserProfile().email.orEmpty(),
                hasAppUpdateTips = IntySetting.hasAppUpdateTips(),
                vipStatus = BillingRepository.vipStatusFlow.value,
            )
        )
    val state: StateFlow<SettingState> = _state.asStateFlow()

    // 对话框状态（保留用于兼容）
    private val _dialogState = MutableStateFlow(DialogState())
    val dialogState: StateFlow<DialogState> = _dialogState.asStateFlow()

    init {
        // 监听 VIP 状态变化
        viewModelScope.launch {
            BillingRepository.vipStatusFlow.collect { vipStatus ->
                _state.value = _state.value.copy(vipStatus = vipStatus)
            }
        }

        // 同步对话框状态到统一状态
        viewModelScope.launch {
            _dialogState.collect { dialogState ->
                _state.value = _state.value.copy(dialogState = dialogState)
            }
        }
    }

    /** 刷新用户ID和更新提示状态（用于响应非响应式数据源的变化） */
    fun refreshUserData() {
        _state.value =
            _state.value.copy(
                userId = IntySetting.getCurUserID(),
                userEmail = UserProfileManager.getUserProfile().email.orEmpty(),
                hasAppUpdateTips = IntySetting.hasAppUpdateTips(),
            )
    }

    /** 显示删除账号对话框 */
    fun showDeleteAccountDialog() {
        _dialogState.value = _dialogState.value.copy(showDeleteAccountDialog = true)
    }

    /** 隐藏删除账号对话框 */
    fun hideDeleteAccountDialog() {
        _dialogState.value = _dialogState.value.copy(showDeleteAccountDialog = false)
    }

    // 删除账号的结果
    val deleteAccountResultFlow = MutableStateFlow(false)

    /** 重置删除账号结果状态 */
    fun resetDeleteAccountResult() {
        deleteAccountResultFlow.value = false
    }

    /** 重置所有对话框状态 */
    fun resetDialogState() {
        _dialogState.value = DialogState()
        _state.value = _state.value.copy(dialogState = DialogState())
    }

    /** 删除账号（已包含删除检查逻辑） */
    fun deleteUserAccount() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = NetServiceMgr.getUserApi().userDeleteAccount()

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            if (result.data.success) {
                                deleteAccountResultFlow.emit(true)
                            } else {
                                // 删除失败，显示后端返回的错误信息
                                val errorMessage =
                                    result.data.message
                                        ?: Utils.getApp()
                                            .getString(R.string.toast_account_deletion_error)

                                // 如果错误信息包含订阅相关关键词，显示特定的提示
                                if (
                                    errorMessage.contains("订阅", ignoreCase = true) ||
                                        errorMessage.contains("subscription", ignoreCase = true)
                                ) {
                                    ToastUtils.showShort(
                                        Utils.getApp()
                                            .getString(R.string.toast_cancel_subscription_first)
                                    )
                                } else {
                                    ToastUtils.showShort(errorMessage)
                                }
                            }
                        }

                        is HttpResult.Failure -> {
                            // 检查错误消息是否包含订阅相关关键词
                            val errorMessage = result.message
                            if (
                                errorMessage.contains("订阅", ignoreCase = true) ||
                                    errorMessage.contains("subscription", ignoreCase = true)
                            ) {
                                ToastUtils.showShort(
                                    Utils.getApp()
                                        .getString(R.string.toast_cancel_subscription_first)
                                )
                            } else {
                                // 如果有错误消息，显示错误消息；否则显示通用错误
                                if (errorMessage.isNotEmpty()) {
                                    ToastUtils.showShort(errorMessage)
                                } else {
                                    ToastUtils.showShort(
                                        Utils.getApp()
                                            .getString(R.string.toast_account_deletion_error)
                                    )
                                }
                            }
                        }
                    }
                }
            } catch (e: HttpException) {
                // 专门处理HTTP异常
                LogUtils.e("deleteUserAccount HTTP Exception: ${e.code()} - ${e.message()}")
                val errorMessage = HttpErrorHandler.handleHttpException(e, "account")
                withContext(Dispatchers.Main) { ToastUtils.showShort(errorMessage) }
            } catch (e: Exception) {
                LogUtils.e("删除用户账号 exception: ${e.message}")
                val errorMessage = HttpErrorHandler.handleGeneralException(e, "account")
                withContext(Dispatchers.Main) { ToastUtils.showShort(errorMessage) }
            }
        }
    }
}

/** 对话框状态数据类 */
data class DialogState(val showDeleteAccountDialog: Boolean = false)
