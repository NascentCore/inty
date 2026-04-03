package com.ai.intellimate

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.common.event.EventBus
import ai.sxwl.android.common.event.EventSubscriber
import ai.sxwl.android.common.event.PushNotificationEvent
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AppVersionRsp
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.api.model.VersionReminderAction
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.firebase.FCMConstants
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.audio.AudioManager
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.main.data.MainRepository
import com.ai.intellimate.utils.CredentialManagerHelper.clearCredentialState
import com.ai.intellimate.utils.UnifiedStartupManager
import com.ai.intellimate.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeout

enum class HomeTabIndex {
    Chat,
    Messages,
    Create,
    Explore,
    Profile,
}

class MainViewModel : BaseVM() {

    private val mainRepository = MainRepository()

    val followingAgents = mutableStateListOf<AgentInfo>() // 关注的agents列表数据

    private val _selectedTab = MutableStateFlow(getInitialTabFromRemoteConfig())
    val selectedTab = _selectedTab.asStateFlow()

    private val _currentChatPageIndex = MutableStateFlow(0)
    val currentChatPageIndex = _currentChatPageIndex.asStateFlow()

    val userProfile =
        UserProfileManager.profile.stateIn(viewModelScope, SharingStarted.Eagerly, UserProfile())

    // 登录状态StateFlow，用于UI响应登录状态变化
    private val _isLoggedIn =
        MutableStateFlow(IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty())
    val isLoggedIn: StateFlow<Boolean> = _isLoggedIn.asStateFlow()

    // 显示设置界面状态
    private val _showSettings = MutableStateFlow(false)
    val showSettings: StateFlow<Boolean> = _showSettings.asStateFlow()

    // Explore页面重置到顶部信号（用于底部导航栏双击）
    private val _exploreResetSignal = MutableStateFlow(0)
    val exploreResetSignal: StateFlow<Int> = _exploreResetSignal.asStateFlow()

    private val _messagesTabHasPush = MutableStateFlow(IntySetting.hasMessagesTabPush())
    val messagesTabHasPush: StateFlow<Boolean> = _messagesTabHasPush.asStateFlow()

    // appUpdateTips 只存在于内存中，每次重启都会重置为 false
    private val _appUpdateTips = MutableStateFlow(false)
    val appUpdateTips: StateFlow<Boolean> = _appUpdateTips.asStateFlow()
    private val _appUpdateTipsRedDot = MutableStateFlow(false)
    val appUpdateTipsRedDot: StateFlow<Boolean> = _appUpdateTipsRedDot.asStateFlow()

    private val tabHistory = ArrayDeque<HomeTabIndex>()

    // 标记用户是否已经手动切换过tab，如果已切换，则不再根据remote config自动更新
    private var hasUserManuallySelectedTab = false

    // 反馈请求弹窗显示状态
    private val _showFeedbackRequestDialog = MutableStateFlow(false)
    val showFeedbackRequestDialog: StateFlow<Boolean> = _showFeedbackRequestDialog.asStateFlow()
    val subLimit = mainRepository.subLimit

    private val pushMessageSubscriber =
        object : EventSubscriber<PushNotificationEvent.MessageReceived> {
            override fun onEvent(event: PushNotificationEvent.MessageReceived) {
                handlePushMessageEvent(event)
            }
        }

    // 点击离线推送通知相关（存储点击过来的AgentId）
    private var _pushAgentId = MutableStateFlow("")
    val pushAgentId: StateFlow<String> = _pushAgentId.asStateFlow()

    /** 节日记忆推送点击：跳转 Love Journal 页并定位到对应记忆条目。Pair(agentId, memoryId)，memoryId 可为 null。 */
    private var _pushFestivalMemoryTarget = MutableStateFlow<Pair<String, Long?>?>(null)
    val pushFestivalMemoryTarget: StateFlow<Pair<String, Long?>?> =
        _pushFestivalMemoryTarget.asStateFlow()

    // 首次登陆时，记录跳转注册页面时的动作
    private val _needsRegInfo = MutableStateFlow(false)
    val needsRegInfo: StateFlow<Boolean> = _needsRegInfo.asStateFlow()

    companion object {
        private const val MAX_TAB_HISTORY = 10
    }

    init {
        updateLoginState()
        subscribePushEvents()

        viewModelScope.launch(Dispatchers.IO) {
            val initialFetchTime = FirebaseManager.getRemoteConfigLastFetchTime()

            var waitCount = 0
            val maxWaitCount = 30
            while (waitCount < maxWaitCount) {
                delay(100)
                val currentFetchTime = FirebaseManager.getRemoteConfigLastFetchTime()
                if (currentFetchTime > initialFetchTime || waitCount >= maxWaitCount - 1) {
                    break
                }
                waitCount++
            }

            // 只有在用户没有手动切换过tab的情况下，才根据remote config更新
            // 这样可以避免在界面显示后，remote config加载完成时强制切换tab
            if (!hasUserManuallySelectedTab) {
                val newTab = getInitialTabFromRemoteConfig()
                if (newTab != _selectedTab.value) {
                    LogUtils.d(
                        "MainViewModel",
                        "根据 Remote Config 更新 tab: ${_selectedTab.value.name} -> ${newTab.name}",
                    )
                    withContext(Dispatchers.Main) { _selectedTab.value = newTab }
                }
            } else {
                LogUtils.d("MainViewModel", "用户已手动切换过tab，跳过 Remote Config 的自动更新")
            }
        }

        viewModelScope.launch(Dispatchers.IO) { mainRepository.connectWebSocket() }
    }

    private fun getInitialTabFromRemoteConfig(): HomeTabIndex {
        return try {
            val tabIndex =
                FirebaseManager.getRemoteConfigLong(
                        FirebaseManager.RemoteConfigKeys.HOME_PAGE_DEFAULT_TAB_INDEX
                    )
                    .toInt()

            LogUtils.d("MainViewModel", "Remote Config home_page_default_tab_index = $tabIndex")

            val tabEntries = HomeTabIndex.entries.toTypedArray()
            if (tabIndex >= 0 && tabIndex < tabEntries.size) {
                tabEntries[tabIndex]
            } else {
                LogUtils.w(
                    "MainViewModel",
                    "Remote Config tab index ($tabIndex) 越界（有效范围: 0-${tabEntries.size - 1}），使用默认值 Chat tab",
                )
                HomeTabIndex.Chat
            }
        } catch (e: Exception) {
            LogUtils.e("MainViewModel", "获取 Remote Config tab index 失败: ${e.message}", e)
            HomeTabIndex.Chat
        }
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

        viewModelScope.launch {
            isLoggedIn.collect {
                if (it) {
                    // 领取积分
                    BoostManager.checkClaimReward()
                }
            }
        }
    }

    fun loadBusinessData() {
        // 检查app版本更新
        checkAppVersion()
    }

    fun selectTab(tab: Int, trackHistory: Boolean = true) {
        // 防止数组越界，确保tab索引在有效范围内
        val tabEntries = HomeTabIndex.entries.toTypedArray()
        if (tab < 0 || tab >= tabEntries.size) {
            LogUtils.e("selectTab - 无效的tab索引: $tab, 有效范围: 0-${tabEntries.size - 1}")
            return
        }

        // 切换tab时停止所有音频播放
        stopAllAudioPlayback()

        val targetTab = tabEntries[tab]
        val previousTab = _selectedTab.value
        if (previousTab == targetTab) {
            return
        }

        // 如果trackHistory为true，表示这是用户手动切换，标记为已手动选择
        // 这样后续remote config加载完成时，就不会再自动切换tab
        if (trackHistory) {
            hasUserManuallySelectedTab = true
            tabHistory.addLast(previousTab)
            if (tabHistory.size > MAX_TAB_HISTORY) {
                tabHistory.removeFirst()
            }
        }
        _selectedTab.value = targetTab

        if (targetTab == HomeTabIndex.Messages) {
            clearMessagesTabPush()
        }
    }

    /** tab 返回：回到上一个访问的tab */
    fun navigateBackToPreviousTab(): Boolean {
        if (tabHistory.isEmpty()) {
            return false
        }
        val previousTab = tabHistory.removeLast()
        selectTab(previousTab.ordinal, trackHistory = false)
        return true
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

    /** 触发Explore页面重置到顶部（用于底部导航栏双击） */
    fun triggerExploreReset() {
        _exploreResetSignal.value += 1
    }

    /** 清除消息红点状态（进入消息Tab后调用） */
    fun clearMessagesTabPush() {
        if (_messagesTabHasPush.value) {
            _messagesTabHasPush.value = false
        }
        viewModelScope.launch(Dispatchers.IO) { IntySetting.setMessagesTabHasPushSuspend(false) }
    }

    fun clearAppUpdateTipsRedDot() {
        if (_appUpdateTipsRedDot.value) {
            _appUpdateTipsRedDot.value = false
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

                if (!BillingRepository.isInitialized() || !BillingRepository.isConnected()) {
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
                // 获取 FCM Token
                val token = FirebaseManager.registerFCM()
                // 上报 Token 到服务器
                FirebaseManager.uploadFCMToken(token)
            } catch (e: Exception) {
                LogUtils.e("MainViewModel", "登录成功后，获取/上报 FCM Token 失败", e)
                // 失败不影响登录流程，只记录日志
            }
        }
    }

    /** 用户登出方法 */
    fun logout() {
        viewModelScope.launch {
            // 获取当前用户信息用于事件上报
            val currentUserProfile = userProfile.value

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
            tabHistory.clear()
            // 退出登录/删除账号后，将 tab 选择重置为 Remote Config 默认首页
            hasUserManuallySelectedTab = false
            _selectedTab.value = getInitialTabFromRemoteConfig()

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

            // ✅ 修复：清理 Room 数据库，避免数据残留
            try {
                ai.sxwl.android.data.di.DataModule.getChatRepository().clearAllChatData()
                LogUtils.i("MainViewModel.logout: cleared all chat data")
            } catch (e: Exception) {
                LogUtils.e("MainViewModel.logout: failed to clear chat data: ${e.message}")
            }

            // 清除凭证状态 - 通知所有凭证提供者清除存储的凭证会话
            // 参考:
            // https://developer.android.com/identity/sign-in/credential-manager-siwg#handle-sign-out
            try {
                clearCredentialState(Utils.getApp())
            } catch (e: Exception) {
                LogUtils.e("Failed to clear credential state during logout: ${e.message}")
            }

            // 更新登录状态，触发UI更新
            // 注意：hideSettings() 已经在上方调用，所以这里更新状态后，UI会直接从 SettingContent 切换到 SplashLoginUI
            updateLoginState()
        }
    }

    /** 检查app版本更新 */
    private val _needForceUpgrade = Channel<AppVersionRsp.AppVersionData?>()
    val needForceUpgrade = _needForceUpgrade.receiveAsFlow()

    private fun checkAppVersion() = launchBackground {
        val timeoutMs: Long = 10000
        try {
            when (
                val result =
                    withTimeout(timeoutMs) { NetServiceMgr.getCommonApi().checkAppUpgrade() }
            ) {
                is HttpResult.Success -> {
                    val rsp = result.data
                    LogUtils.d("版本升级信息:$rsp")
                    when (rsp.reminder_action) {
                        VersionReminderAction.BLOCK_ACCESS,
                        VersionReminderAction.POP_UP_REMINDER -> {
                            // 设置更新提示（仅内存状态）
                            _appUpdateTips.value = true
                            _appUpdateTipsRedDot.value = true
                            // 需要显示更新弹窗（强制拦截或弹窗提醒）
                            _needForceUpgrade.send(rsp)
                        }
                        VersionReminderAction.SETTINGS_REMINDER -> {
                            // 设置更新提示（仅内存状态）
                            _appUpdateTips.value = true
                            _appUpdateTipsRedDot.value = true
                        }
                        VersionReminderAction.NONE,
                        null -> {
                            // 当版本不需要更新时（reminder_action 为 NONE），清除更新提示
                            if (_appUpdateTips.value) {
                                _appUpdateTips.value = false
                                _appUpdateTipsRedDot.value = false
                            }
                        }
                    }
                }

                is HttpResult.Failure -> {
                    LogUtils.w("MainViewModel", "checkAppVersion: 版本检查失败 - ${result.message}")
                    // 版本检查失败时，不清除更新提示（保持之前的状态，避免误清除）
                    // 如果确实需要清除，应该等待下次成功的版本检查返回 NONE
                }
            }
        } catch (e: TimeoutCancellationException) {
            LogUtils.w("Version check timeout after ${timeoutMs}ms")
            // 版本检查超时时，不清除更新提示（保持之前的状态，避免误清除）
        }
    }

    override fun onCleared() {
        EventBus.unsubscribe(PushNotificationEvent.MessageReceived::class, pushMessageSubscriber)
        super.onCleared()
    }

    private fun subscribePushEvents() {
        EventBus.subscribe(PushNotificationEvent.MessageReceived::class, pushMessageSubscriber)
    }

    private fun handlePushMessageEvent(event: PushNotificationEvent.MessageReceived) {
        when (event.type) {
            FCMConstants.TYPE_AGENT_MESSAGE -> {
                val agentId = event.data[FCMConstants.DATA_KEY_AGENT_ID]
                if (!agentId.isNullOrBlank()) {
                            viewModelScope.launch(Dispatchers.IO) {
                                IntySetting.setConversationHasPushSuspend(agentId, true)
                            }
                }
                if (!_messagesTabHasPush.value) {
                    _messagesTabHasPush.value = true
                }
                viewModelScope.launch(Dispatchers.IO) {
                    IntySetting.setMessagesTabHasPushSuspend(true)
                }
            }
            FCMConstants.TYPE_FEEDBACK_REQUEST -> {
                // feedback_request 类型消息由 MainActivity 判断是否在前台后处理
                // 这里只记录日志，不直接显示弹窗
                LogUtils.d("MainViewModel", "收到 feedback_request 类型消息")
            }
        }
    }

    /** 显示反馈请求弹窗 */
    fun showFeedbackRequestDialog() {
        _showFeedbackRequestDialog.value = true
    }

    /** 隐藏反馈请求弹窗 */
    fun hideFeedbackRequestDialog() {
        _showFeedbackRequestDialog.value = false
    }

    /** 更新 pushAgentId (离线推送通知点击) */
    fun updatePushAgentId(id: String) {
        _pushAgentId.value = id
    }

    /** 更新节日记忆推送目标 (点击节日记忆通知后跳转 Love Journal) */
    fun updatePushFestivalMemoryTarget(agentId: String, memoryId: Long?) {
        _pushFestivalMemoryTarget.value = Pair(agentId, memoryId)
    }

    /** 清除节日记忆推送目标（导航完成后调用） */
    fun clearPushFestivalMemoryTarget() {
        _pushFestivalMemoryTarget.value = null
    }

    /** 更新 needsRegInfo (首次登录跳转完善资料页面) */
    fun updateNeedsRegInfo(value: Boolean) {
        _needsRegInfo.value = value
    }
}
