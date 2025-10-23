package com.ai.inty.viewmodels

import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import androidx.lifecycle.viewModelScope
import com.ai.inty.R
import com.ai.inty.base.BaseViewModel
import com.ai.inty.billing.VipStatusHelper
import com.ai.inty.net.IUserApi
import com.ai.inty.net.NetServiceMgr
import com.architecture.httplib.core.HttpResult
import ai.sxwl.android.data.store.IntySetting
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** 设置页面 ViewModel */
class SettingViewModel : BaseViewModel() {

    private val userApi: IUserApi by lazy { NetServiceMgr.getUserApi() }

    // 设置状态
    private val _settingsState = MutableStateFlow(SettingsState())
    val settingsState: StateFlow<SettingsState> = _settingsState.asStateFlow()

    // 对话框状态
    private val _dialogState = MutableStateFlow(DialogState())
    val dialogState: StateFlow<DialogState> = _dialogState.asStateFlow()

    init {
        loadSettings()
    }

    /** 加载设置 */
    private fun loadSettings() {
        viewModelScope.launch {
            val currentState = _settingsState.value
            _settingsState.value =
                currentState.copy(
                    keepTalking = IntySetting.isShowKeepTalking(),
                    premiumMode = IntySetting.isShowPremiumModel(),
                )
        }
    }

    /** 切换保持对话设置 */
    fun toggleKeepTalking() {
        val newValue = !_settingsState.value.keepTalking
        IntySetting.setShowKeepTalking(newValue)
        _settingsState.value = _settingsState.value.copy(keepTalking = newValue)
    }

    /** 切换高级模型设置 */
    fun togglePremiumMode() {
        VipStatusHelper.checkVipStatus(
            onVip = {
                val newValue = !_settingsState.value.premiumMode
                IntySetting.setShowPremiumModel(newValue)
                _settingsState.value = _settingsState.value.copy(premiumMode = newValue)
            },
            onNotVip = { _dialogState.value = _dialogState.value.copy(showPremiumDialog = true) },
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

    /** 隐藏高级模型对话框 */
    fun hidePremiumDialog() {
        _dialogState.value = _dialogState.value.copy(showPremiumDialog = false)
    }

    /** 检查账号是否有订阅需要取消，才能用来删除账号 */
    fun checkAccountSubscribe() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = userApi.userDeletionCheck()


                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            if (result.data.canDelete && !result.data.activeSubscription) {
                                deleteUserAccount()
                            } else {
                                ToastUtils.showShort(
                                    Utils.getApp().getString(
                                        R.string.toast_cancel_subscription_first
                                    )
                                )
                            }
                        }

                        is HttpResult.Failure -> {
                            ToastUtils.showShort(
                                Utils.getApp().getString(
                                    R.string.toast_check_account_deletion_error
                                )
                            )
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                LogUtils.e("checkAccountSubscribe HTTP Exception: ${e.code()} - ${e.message()}")
                val errorMessage = handleHttpException(e, "account")
                withContext(Dispatchers.Main) { ToastUtils.showShort(errorMessage) }
            } catch (e: Exception) {
                LogUtils.e("检查账号需要取消订阅 exception: ${e.message}")
                val errorMessage = handleGeneralException(e, "account")
                withContext(Dispatchers.Main) { ToastUtils.showShort(errorMessage) }
            }
        }
    }

    // 删除账号的结果
    val deleteAccountResultFlow = MutableStateFlow(false)

    /** 删除账号的接口 */
    private fun deleteUserAccount() {
        launchWithNetCheck {
            try {
                val result = userApi.userDeleteAccount()


                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            deleteAccountResultFlow.emit(true)
                        }

                        is HttpResult.Failure -> {
                            ToastUtils.showShort(
                                Utils.getApp().getString(R.string.toast_account_deletion_error)
                            )
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                LogUtils.e("deleteUserAccount HTTP Exception: ${e.code()} - ${e.message()}")
                val errorMessage = handleHttpException(e, "account")
                withContext(Dispatchers.Main) { ToastUtils.showShort(errorMessage) }
            } catch (e: Exception) {
                LogUtils.e("删除用户账号 exception: ${e.message}")
                val errorMessage = handleGeneralException(e, "account")
                withContext(Dispatchers.Main) { ToastUtils.showShort(errorMessage) }
            }
        }
    }
}

/** 设置状态数据类 */
data class SettingsState(val keepTalking: Boolean = false, val premiumMode: Boolean = false)

/** 对话框状态数据类 */
data class DialogState(
    val showDeleteAccountDialog: Boolean = false,
    val showPremiumDialog: Boolean = false,
)
