package com.ai.intellimate.settings

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.IUserApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.R
import com.ai.intellimate.utils.HttpErrorHandler
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException

/** 设置页面 ViewModel */
class SettingViewModel : BaseVM() {
    private val userApi: IUserApi by lazy { NetServiceMgr.getUserApi() }

    // 对话框状态
    private val _dialogState = MutableStateFlow(DialogState())
    val dialogState: StateFlow<DialogState> = _dialogState.asStateFlow()

    /** 显示删除账号对话框 */
    fun showDeleteAccountDialog() {
        _dialogState.value = _dialogState.value.copy(showDeleteAccountDialog = true)
    }

    /** 隐藏删除账号对话框 */
    fun hideDeleteAccountDialog() {
        _dialogState.value = _dialogState.value.copy(showDeleteAccountDialog = false)
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
                                    Utils.getApp()
                                        .getString(R.string.toast_cancel_subscription_first),
                                )
                            }
                        }
                        is HttpResult.Failure -> {
                            ToastUtils.showShort(
                                Utils.getApp()
                                    .getString(R.string.toast_check_account_deletion_error),
                            )
                        }
                    }
                }
            } catch (e: HttpException) {
                // 专门处理HTTP异常
                LogUtils.e("checkAccountSubscribe HTTP Exception: ${e.code()} - ${e.message()}")
                val errorMessage = HttpErrorHandler.handleHttpException(e, "account")
                withContext(Dispatchers.Main) { ToastUtils.showShort(errorMessage) }
            } catch (e: Exception) {
                LogUtils.e("检查账号需要取消订阅 exception: ${e.message}")
                val errorMessage = HttpErrorHandler.handleGeneralException(e, "account")
                withContext(Dispatchers.Main) { ToastUtils.showShort(errorMessage) }
            }
        }
    }

    // 删除账号的结果
    val deleteAccountResultFlow = MutableStateFlow(false)

    /** 删除账号的接口 */
    private fun deleteUserAccount() {
        launchBackground {
            try {
                val result = userApi.userDeleteAccount()

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            deleteAccountResultFlow.emit(true)
                        }
                        is HttpResult.Failure -> {
                            ToastUtils.showShort(
                                Utils.getApp().getString(R.string.toast_account_deletion_error),
                            )
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
data class DialogState(
    val showDeleteAccountDialog: Boolean = false,
    val showPremiumDialog: Boolean = false,
)
