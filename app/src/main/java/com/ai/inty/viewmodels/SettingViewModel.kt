package com.ai.inty.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.billing.BillingRepository
import com.inty.utils.storage.IntySetting
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * 设置页面 ViewModel
 */
class SettingViewModel : ViewModel() {

    // 设置状态
    private val _settingsState = MutableStateFlow(SettingsState())
    val settingsState: StateFlow<SettingsState> = _settingsState.asStateFlow()

    // 对话框状态
    private val _dialogState = MutableStateFlow(DialogState())
    val dialogState: StateFlow<DialogState> = _dialogState.asStateFlow()

    init {
        loadSettings()
    }

    /**
     * 加载设置
     */
    private fun loadSettings() {
        viewModelScope.launch {
            val currentState = _settingsState.value
            _settingsState.value = currentState.copy(
                keepTalking = IntySetting.isShowKeepTalking(),
                premiumMode = IntySetting.isShowPremiumModel()
            )
        }
    }

    /**
     * 切换保持对话设置
     */
    fun toggleKeepTalking() {
        val newValue = !_settingsState.value.keepTalking
        IntySetting.setShowKeepTalking(newValue)
        _settingsState.value = _settingsState.value.copy(keepTalking = newValue)
    }

    /**
     * 切换高级模型设置
     */
    fun togglePremiumMode() {
        val vipStatus = BillingRepository.vipStatusFlow.value
        if (!vipStatus.isSubscribed) {
            // 非会员，显示高级模型对话框
            _dialogState.value = _dialogState.value.copy(showPremiumDialog = true)
        } else {
            val newValue = !_settingsState.value.premiumMode
            IntySetting.setShowPremiumModel(newValue)
            _settingsState.value = _settingsState.value.copy(premiumMode = newValue)
        }
    }

    /**
     * 显示删除账号对话框
     */
    fun showDeleteAccountDialog() {
        _dialogState.value = _dialogState.value.copy(showDeleteAccountDialog = true)
    }

    /**
     * 隐藏删除账号对话框
     */
    fun hideDeleteAccountDialog() {
        _dialogState.value = _dialogState.value.copy(showDeleteAccountDialog = false)
    }

    /**
     * 隐藏高级模型对话框
     */
    fun hidePremiumDialog() {
        _dialogState.value = _dialogState.value.copy(showPremiumDialog = false)
    }

    /**
     * 确认删除账号
     */
    fun confirmDeleteAccount() {
        // 这里可以调用删除账号的 API
        hideDeleteAccountDialog()
    }
}

/**
 * 设置状态数据类
 */
data class SettingsState(
    val keepTalking: Boolean = false,
    val premiumMode: Boolean = false
)

/**
 * 对话框状态数据类
 */
data class DialogState(
    val showDeleteAccountDialog: Boolean = false,
    val showPremiumDialog: Boolean = false
) 