package com.ai.inty.viewmodels

import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import androidx.compose.runtime.mutableStateListOf
import androidx.lifecycle.viewModelScope
import com.ai.inty.R
import com.ai.inty.base.BaseViewModel
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.AppVersionRsp
import com.ai.inty.beans.CreateAgentRequest
import com.ai.inty.beans.UserProfile
import com.ai.inty.billing.BillingRepository
import com.ai.inty.chat.ChatViewModel
import com.ai.inty.net.IAgentApi
import com.ai.inty.net.ICommonApi
import com.ai.inty.net.NetServiceMgr
import com.ai.inty.utils.AgentCacheManager
import com.ai.inty.utils.CredentialManagerHelper.clearCredentialState
import com.ai.inty.utils.FirebasePerformanceHelper
import com.ai.inty.utils.IntyUserProfileSDK
import com.ai.inty.utils.UnifiedStartupManager
import com.ai.inty.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class HomeTabIndex {
    Chat,
    Conversation,
    Create,
    Explore,
    Profile,
}

class MainViewModel : BaseViewModel() {

    private val agentApi: IAgentApi by lazy { NetServiceMgr.getAgentApi() }

    private val commonApi: ICommonApi by lazy { NetServiceMgr.getCommonApi() }

    val followingAgents = mutableStateListOf<AgentInfo>() // 关注的agents列表数据
    val userCreatedAgents = mutableStateListOf<AgentInfo>() // 用户自创建的agents数据

    // Pagination state for user created agents
    private var currentUserAgentsPage = 0
    private var _isLoadingUserAgents = MutableStateFlow(false)
    val isLoadingUserAgents = _isLoadingUserAgents.asStateFlow()
    private var hasMoreUserAgents = true

    // 刷新状态，用于区分首次加载和刷新操作
    private var _isRefreshingUserAgents = MutableStateFlow(false)
    val isRefreshingUserAgents = _isRefreshingUserAgents.asStateFlow()

    private val _selectedTab = MutableStateFlow(HomeTabIndex.Chat)
    val selectedTab = _selectedTab.asStateFlow()

    private val _currentChatPageIndex = MutableStateFlow(0)
    val currentChatPageIndex = _currentChatPageIndex.asStateFlow()

    private var chatViewModel: ChatViewModel? = null

    // 使用flow数据流的形式，感知用户数据
    private val _userProfile = MutableStateFlow(UserProfile())
    val userProfile = _userProfile.asStateFlow()


    init {
        // 使用统一启动管理器的数据快速初始化UI
        loadStartupData()
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

    fun updateUserInfoLocal() {
        _userProfile.update {
            UserProfileManager.getUserProfile()
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
        when (_selectedTab.value) {
            HomeTabIndex.Conversation -> {
                chatViewModel?.getConversations()
            }

            HomeTabIndex.Profile -> {
                // 使用refreshCreatedAgentsListIfOnTab()来避免重复请求
                // 这样可以在一个地方统一管理Profile tab的数据刷新逻辑
                refreshCreatedAgentsListIfOnTab()
            }

            else -> {}
        }
    }

    /** 停止所有音频播放 用于tab切换时确保音频停止 */
    private fun stopAllAudioPlayback() {
        try {
            // 通过AudioManager单例停止所有播放
            val audioManager =
                com.ai.inty.audio.AudioManager.getInstance(Utils.getApp(), viewModelScope)
            audioManager.stopAllPlayback()
        } catch (e: Exception) {
            LogUtils.e("MainViewModel - 停止音频播放失败: ${e.message}")
        }
    }

    fun setChatViewModel(chatViewModel: ChatViewModel) {
        this.chatViewModel = chatViewModel
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
            } catch (e: kotlinx.coroutines.CancellationException) {
                LogUtils.e("BillingRepository MainViewModel Member status update cancelled: ${e.message}")
                // 协程被取消是正常情况，不需要特殊处理
            } catch (e: Exception) {
                LogUtils.e("BillingRepository MainViewModel Member status update failed: ${e.message}")
                // 不影响主流程，静默处理
            }
        }
    }

    fun getUserCreatedAgents() {
        currentUserAgentsPage = 0
        hasMoreUserAgents = true

        // 如果已经有数据，则使用静默刷新，不显示loading
        if (userCreatedAgents.isNotEmpty()) {
            loadUserCreatedAgentsSilently()
        } else {
            // 没有数据时才清空并显示loading
            userCreatedAgents.clear()
            loadUserCreatedAgents()
        }
    }

    fun loadMoreUserCreatedAgents() {
        if (!_isLoadingUserAgents.value && hasMoreUserAgents) {
            currentUserAgentsPage++
            loadUserCreatedAgents()
        }
    }

    private fun loadUserCreatedAgentsSilently() {
        if (_isRefreshingUserAgents.value) return

        _isRefreshingUserAgents.value = true
        val skip = currentUserAgentsPage * 10

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.getUserCreatedAgents(skip, 10)

                when (result) {
                    is HttpResult.Success -> {
                        if (result.data.isEmpty()) {
                            hasMoreUserAgents = false
                            LogUtils.d("loadUserCreatedAgentsSilently - No more user created agents to load")
                        } else {
                            // 静默更新数据，直接替换
                            userCreatedAgents.clear()
                            userCreatedAgents.addAll(result.data)
                            LogUtils.d("loadUserCreatedAgentsSilently - 静默更新数据: ${result.data.size}个")
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("loadUserCreatedAgentsSilently - API failure: ${result.message}")
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("loadUserCreatedAgentsSilently exception: ${e.message}")
            } finally {
                _isRefreshingUserAgents.value = false
            }
        }
    }

    private fun loadUserCreatedAgents() {
        if (_isLoadingUserAgents.value) return

        _isLoadingUserAgents.value = true
        val skip = currentUserAgentsPage * 10

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.getUserCreatedAgents(skip, 10)

                when (result) {
                    is HttpResult.Success -> {
                        if (result.data.isEmpty()) {
                            hasMoreUserAgents = false
                        } else {
                            if (currentUserAgentsPage == 0) {
                                // 第一页，直接替换（这里才清空并替换数据）
                                userCreatedAgents.clear()
                                userCreatedAgents.addAll(result.data)
                                LogUtils.i("loadUserCreatedAgents - 替换第一页数据: ${result.data.size}个")
                            } else {
                                // 后续页，追加到现有列表
                                userCreatedAgents.addAll(result.data)
                                LogUtils.d("loadUserCreatedAgents - 追加第${currentUserAgentsPage + 1}页数据: ${result.data.size}个，总计: ${userCreatedAgents.size}个")
                            }
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("loadUserCreatedAgents - API failure: ${result.message}")
                        //                        showNetworkAwareError(result.message)
                        // If loading failed, rollback page counter
                        if (currentUserAgentsPage > 0) {
                            currentUserAgentsPage--
                        }
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("loadUserCreatedAgents exception: ${e.message}")
                // If loading failed, rollback page counter
                if (currentUserAgentsPage > 0) {
                    currentUserAgentsPage--
                }
            }
            _isLoadingUserAgents.value = false
        }
    }

    fun refreshCreatedAgentsListIfOnTab() {
        if (_selectedTab.value == HomeTabIndex.Profile) {
            // 如果已经在加载中，避免重复请求
            if (!_isLoadingUserAgents.value && !_isRefreshingUserAgents.value) {
                getUserCreatedAgents()
            } else {
                LogUtils.i("refreshCreatedAgentsListIfOnTab - 跳过刷新，正在加载中")
            }
        }
    }

    /** 创建Ai Agent的接口 */
    fun createAgent(
        request: CreateAgentRequest,
        onSuccess: (AgentInfo) -> Unit,
        onError: (String) -> Unit,
    ) {
        // 开始性能追踪
        FirebasePerformanceHelper.trace("create_agent") { trace ->
            FirebasePerformanceHelper.putAttribute(trace, "agent_name", request.name)
            FirebasePerformanceHelper.putAttribute(
                trace,
                "has_avatar",
                (request.avatar?.isNotEmpty() == true).toString(),
            )
            FirebasePerformanceHelper.putAttribute(
                trace,
                "visibility",
                request.visibility,
            )

            launchWithNetCheck {
                try {
                    val result = agentApi.createAgent(request)

                    withContext(Dispatchers.Main) {
                        when (result) {
                            is HttpResult.Success -> {
                                // 刷新用户创建的角色列表
                                refreshCreatedAgentsListIfOnTab()
                                onSuccess(result.data)
                            }

                            is HttpResult.Failure -> {
                                LogUtils.e("createAgent error: $result")
                                val errorMessage =
                                    result.message.ifBlank {
                                        "Creation failed, please check network connection"
                                    }
                                onError(errorMessage)
                            }
                        }
                    }
                } catch (e: retrofit2.HttpException) {
                    // 专门处理HTTP异常
                    LogUtils.e("createAgent HTTP Exception: ${e.code()} - ${e.message()}")
                    val errorMessage = handleHttpException(e, "create")
                    withContext(Dispatchers.Main) { onError(errorMessage) }
                } catch (e: Exception) {
                    LogUtils.e("createAgent exception: ${e.message}")
                    val errorMessage = handleGeneralException(e, "create")
                    withContext(Dispatchers.Main) { onError(errorMessage) }
                }
            }
        }
    }

    // 新增：用户登出方法
    fun logout() {
        // 清理内存数据
        followingAgents.clear()
        userCreatedAgents.clear()
        _userProfile.value = UserProfile()
        chatViewModel?.clearAllData()

        // 清理统一启动管理器的数据（清空正式用户的数据）
        UnifiedStartupManager.clearAllData()

        // 清理本地存储（这会切换到游客模式）
        IntySetting.logout()
        UserProfileManager.clearUserProfile()

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

        // 切换到游客模式后，重新加载数据
        loadGuestModeData()
    }

    // 游客模式数据加载，游客用户仍然可以访问推荐数据
    private fun loadGuestModeData() {

        viewModelScope.launch {
            try {
                // 更新UI状态
                _userProfile.value = UserProfile()

                // 关键修复：确保用户账户状态正确恢复
                // 游客用户切换后，需要重新设置账户就绪状态
                UnifiedStartupManager.markUserAccountReady()

                // 等待用户账户就绪（游客用户切换需要时间）
                var waitTime = 0
                while (!UnifiedStartupManager.isUserAccountReady() && waitTime < 3000) {
                    delay(100)
                    waitTime += 100
                }

                // 游客用户仍然有有效的token，可以重新加载数据
                // 重新加载agents数据（游客模式也应该有推荐数据）
                UnifiedStartupManager.refreshRecommendedAgents()
                UnifiedStartupManager.refreshChatAgents()
            } catch (e: Exception) {
                LogUtils.e("Failed to load guest mode data: ${e.message}")
            }
        }
    }

    fun deleteAgent(agentId: String, onSuccess: () -> Unit, onError: (String) -> Unit) {
        launchWithNetCheck {
            try {
                val result = agentApi.deleteAgent(agentId)

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            // 从用户创建的角色列表中移除
                            userCreatedAgents.removeAll { it.id == agentId }
                            // 从关注列表中移除（如果存在）
                            followingAgents.removeAll { it.id == agentId }

                            // 同步更新缓存
                            AgentCacheManager.removeAgent(agentId)

                            ToastUtils.showShort(R.string.character_deleted_successfully)
                            onSuccess()
                        }

                        is HttpResult.Failure -> {
                            val errorMessage =
                                result.message.ifBlank {
                                    Utils.getApp().getString(
                                        R.string.operation_failed_check_network,
                                        Utils.getApp().getString(R.string.delete_failed),
                                        Utils.getApp().getString(R.string.check_network_connection),
                                    )
                                }
                            ToastUtils.showShort(
                                Utils.getApp().getString(
                                    R.string.delete_failed_with_reason,
                                    errorMessage
                                )
                            )
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                LogUtils.e("deleteAgent HTTP Exception: ${e.code()} - ${e.message()}")
                val errorMessage = handleHttpException(e, "delete")
                withContext(Dispatchers.Main) {
                    ToastUtils.showShort(errorMessage)
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                LogUtils.e("deleteAgent exception: ${e.message}")
                val errorMessage = handleGeneralException(e, "delete")
                withContext(Dispatchers.Main) {
                    ToastUtils.showShort(errorMessage)
                    onError(errorMessage)
                }
            }
        }
    }

    fun updateAgent(
        agentId: String,
        request: CreateAgentRequest,
        onSuccess: (AgentInfo) -> Unit,
        onError: (String) -> Unit,
    ) {
        LogUtils.i("updateAgent: $agentId")
        launchWithNetCheck {
            try {
                val result = agentApi.updateAgent(agentId, request)

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            // 刷新用户创建的角色列表
                            refreshCreatedAgentsListIfOnTab()
                            // Toast removed to avoid duplicate - handled by calling activity
                            onSuccess(result.data)
                        }

                        is HttpResult.Failure -> {
                            LogUtils.e("updateAgent error: $result")
                            val errorMessage =
                                result.message.ifBlank {
                                    Utils.getApp().getString(
                                        R.string.operation_failed_check_network,
                                        Utils.getApp().getString(R.string.update_failed),
                                        Utils.getApp().getString(R.string.check_network_connection),
                                    )
                                }
                            ToastUtils.showShort(
                                Utils.getApp().getString(
                                    R.string.update_failed_with_reason,
                                    errorMessage
                                )
                            )
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: retrofit2.HttpException) {
                // 专门处理HTTP异常
                LogUtils.e("updateAgent HTTP Exception: ${e.code()} - ${e.message()}")
                val errorMessage = handleHttpException(e, "update")
                withContext(Dispatchers.Main) {
                    ToastUtils.showShort(errorMessage)
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                LogUtils.e("updateAgent exception: ${e.message}")
                val errorMessage = handleGeneralException(e, "update")
                withContext(Dispatchers.Main) {
                    ToastUtils.showShort(errorMessage)
                    onError(errorMessage)
                }
            }
        }
    }

    /** 检查app版本更新 */
    val needForceUpgrade = MutableStateFlow<AppVersionRsp.AppVersionData?>(null)

    private fun checkAppVersion() = launchWithNetCheck {
        val result = commonApi.checkAppUpgrade()
        when (result) {
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
