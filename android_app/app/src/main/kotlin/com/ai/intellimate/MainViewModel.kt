package com.ai.intellimate

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.ICommonApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AppVersionRsp
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.audio.AudioManager
import com.ai.intellimate.utils.CredentialManagerHelper.clearCredentialState
import com.ai.intellimate.utils.IntyUserProfileSDK
import com.ai.intellimate.utils.UnifiedStartupManager
import com.ai.intellimate.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

enum class HomeTabIndex {
    Chat,
    Conversation,
    Create,
    Explore,
    Profile,
}

class MainViewModel : BaseVM() {

    private val commonApi: ICommonApi by lazy { NetServiceMgr.getCommonApi() }

    val followingAgents = mutableStateListOf<AgentInfo>() // 关注的agents列表数据

    private val _selectedTab = MutableStateFlow(HomeTabIndex.Chat)
    val selectedTab = _selectedTab.asStateFlow()

    private val _currentChatPageIndex = MutableStateFlow(0)
    val currentChatPageIndex = _currentChatPageIndex.asStateFlow()

    // 使用flow数据流的形式，感知用户数据
    private val _userProfile = MutableStateFlow(UserProfile())
    val userProfile = _userProfile.asStateFlow()

    // 登录状态StateFlow，用于UI响应登录状态变化
    private val _isLoggedIn =
        MutableStateFlow(IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty())
    val isLoggedIn: StateFlow<Boolean> = _isLoggedIn.asStateFlow()

    // 显示设置界面状态
    private val _showSettings = MutableStateFlow(false)
    val showSettings: StateFlow<Boolean> = _showSettings.asStateFlow()

    init {
        // 使用统一启动管理器的数据快速初始化UI
        loadStartupData()
        // 初始化登录状态
        updateLoginState()
    }

    /** 显示设置界面 */
    fun showSettings() {
        _showSettings.value = true
    }

    /** 隐藏设置界面 */
    fun hideSettings() {
        _showSettings.value = false
    }

    /** 更新登录状态 */
    fun updateLoginState() {
        _isLoggedIn.value = IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
    }

    /** 加载启动数据（快速展示） 从统一启动管理器获取预加载的数据 */
    private fun loadStartupData() {
        // 从统一启动管理器获取用户信息
        val startupUserProfile = UnifiedStartupManager.getCurrentUserProfile()
        if (startupUserProfile != null) {
            _userProfile.value = startupUserProfile
            LogUtils.i("MainViewModel - 使用启动管理器用户信息: ${startupUserProfile.nickname}")
        }
    }

    fun loadBusinessData() {
        // 检查app版本更新
        checkAppVersion()
    }

    fun selectTab(tab: Int) {
        // 防止数组越界，确保tab索引在有效范围内
        val tabEntries = HomeTabIndex.entries.toTypedArray()
        if (tab < 0 || tab >= tabEntries.size) {
            LogUtils.e("selectTab - 无效的tab索引: $tab, 有效范围: 0-${tabEntries.size - 1}")
            return
        }

        // 切换tab时停止所有音频播放
        stopAllAudioPlayback()

        _selectedTab.value = tabEntries[tab]
    }

    /** 停止所有音频播放 用于tab切换时确保音频停止 */
    private fun stopAllAudioPlayback() {
        try {
            // 通过AudioManager单例停止所有播放
            val audioManager = AudioManager.getInstance(Utils.getApp(), viewModelScope)
            audioManager.stopAllPlayback()
        } catch (e: Exception) {
            LogUtils.e("MainViewModel - 停止音频播放失败: ${e.message}")
        }
    }

    fun updateCurrentChatPageIndex(index: Int) {
        _currentChatPageIndex.value = index
    }

    /** 接口请求获取用户信息 */
    fun getUserProfile() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val userProfile = IntyUserProfileSDK.getUserProfile()
                if (userProfile != null) {
                    _userProfile.value = userProfile
                    // 更新本地缓存
                    UserProfileManager.saveUserProfile(userProfile)
                    LogUtils.i("Updated user profile from server: $userProfile")
                } else {
                    LogUtils.e("getUserProfile failure: Failed to get user profile")
                }
            } catch (e: Exception) {
                LogUtils.e("getUserProfile exception: ${e.message}")
            }
        }
    }

    // 感知接口获取到的用户订阅状态
    val vipStatusFlow = BillingRepository.vipStatusFlow
    val vipPlanFlow = BillingRepository.plansFlow

    /** 异步更新订阅计划列表和会员状态 */
    fun updatePlans() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                // 等待BillingRepository初始化完成
                var retryCount = 0
                while (!BillingRepository.isInitialized() && retryCount < 10) {
                    delay(500) // 等待500ms
                    retryCount++
                }

                if (!BillingRepository.isInitialized()) {
                    LogUtils.i("BillingRepository MainViewModel BillingRepository 初始化超时，跳过更新")
                    return@launch
                }

                // 检查BillingRepository是否已连接
                if (!BillingRepository.isConnected()) {
                    LogUtils.i("BillingRepository MainViewModel BillingRepository 未连接，跳过更新")
                    return@launch
                }

                BillingRepository.fetchRemote()
            } catch (e: CancellationException) {
                LogUtils.e(
                    "BillingRepository MainViewModel Member status update cancelled: ${e.message}"
                )
                // 协程被取消是正常情况，不需要特殊处理
            } catch (e: Exception) {
                LogUtils.e(
                    "BillingRepository MainViewModel Member status update failed: ${e.message}"
                )
                // 不影响主流程，静默处理
            }
        }
    }

    /**
     * 登录成功后，主动获取并上报 FCM Token
     *
     * 如果用户在未登录时获取了 Token，登录后需要主动上报
     */
    fun uploadFCMTokenAfterLogin() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                LogUtils.d("MainViewModel", "登录成功后，开始获取并上报 FCM Token")

                // 获取 FCM Token
                val token = FirebaseManager.registerFCM()
                LogUtils.d("MainViewModel", "FCM Token 获取成功: $token")

                // 上报 Token 到服务器
                FirebaseManager.uploadFCMToken(token)
                LogUtils.i("MainViewModel", "登录成功后，FCM Token 上报完成")
            } catch (e: Exception) {
                LogUtils.e("MainViewModel", "登录成功后，获取/上报 FCM Token 失败", e)
                // 失败不影响登录流程，只记录日志
            }
        }
    }

    /** 用户登出方法 */
    fun logout() {
        // 获取当前用户信息用于事件上报
        val currentUserProfile = _userProfile.value

        // 上报用户登出事件
        FirebaseManager.logEvent(
            FirebaseManager.Events.USER_LOGOUT,
            FirebaseManager.safeEventParams(
                "user_id" to currentUserProfile.id,
                "user_name" to currentUserProfile.nickname,
                "logout_method" to "manual",
                "timestamp" to System.currentTimeMillis(),
            ),
        )

        // 清理内存数据
        followingAgents.clear()
        _userProfile.value = UserProfile()

        // 清理统一启动管理器的数据
        UnifiedStartupManager.clearAllData()

        // 先隐藏设置界面，避免UI闪动
        // 这样在状态切换时，UI会直接从 SettingContent 切换到 SplashLoginUI，而不是先显示 SettingContent
        hideSettings()

        // 清理本地存储
        IntySetting.setToken("")
        // 清除用户ID，通过 changeUser("") 来清空当前用户，这样 isLogin() 会返回 false
        IntySetting.changeUser("")
        UserProfileManager.clearUserProfile()

        // 更新登录状态，触发UI更新
        // 注意：hideSettings() 已经在上方调用，所以这里更新状态后，UI会直接从 SettingContent 切换到 SplashLoginUI
        updateLoginState()

        // 清除凭证状态 - 通知所有凭证提供者清除存储的凭证会话
        // 参考:
        // https://developer.android.com/identity/sign-in/credential-manager-siwg#handle-sign-out
        viewModelScope.launch {
            try {
                clearCredentialState(Utils.getApp())
            } catch (e: Exception) {
                LogUtils.e("Failed to clear credential state during logout: ${e.message}")
            }
        }
    }

    /** 检查app版本更新 */
    val needForceUpgrade = MutableStateFlow<AppVersionRsp.AppVersionData?>(null)

    private fun checkAppVersion() = launchBackground {
        when (val result = commonApi.checkAppUpgrade()) {
            is HttpResult.Success -> {
                val rsp = result.data
                if (rsp.update_required && rsp.force_update) {
                    // 有更新，且需要强制更新
                    needForceUpgrade.emit(rsp)
                }
                IntySetting.setAppUpdateTips(rsp.update_required)
                IntySetting.setAppGooglePlayUrl(rsp.download_url ?: "")
            }

            is HttpResult.Failure -> {
                LogUtils.w("result.message")
            }
        }
    }
}
