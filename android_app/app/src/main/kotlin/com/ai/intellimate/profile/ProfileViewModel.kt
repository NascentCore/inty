package com.ai.intellimate.profile

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import androidx.lifecycle.viewModelScope
import com.ai.intellimate.R
import com.ai.intellimate.utils.AgentCacheManager
import com.ai.intellimate.utils.HttpErrorHandler
import com.ai.intellimate.utils.IntyUserProfileSDK
import com.ai.intellimate.utils.UserProfileManager
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException

/** Profile 页面 ViewModel 负责管理用户创建的 Agents 列表、用户信息等 */
class ProfileViewModel : BaseVM() {

    private val agentApi: IAgentApi by lazy { NetServiceMgr.getAgentApi() }

    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState = _uiState.asStateFlow()

    private var currentPage = 0
    private val PAGE_SIZE = 20
    private var hasMore = true

    init {
        loadUserProfile()
    }

    /** 加载用户信息 */
    fun loadUserProfile() {
        viewModelScope.launch(Dispatchers.IO) {
            try {
                val userProfile = IntyUserProfileSDK.getUserProfile()
                if (userProfile != null) {
                    _uiState.update { it.copy(userProfile = userProfile) }
                    UserProfileManager.saveUserProfile(userProfile)
                    LogUtils.i("ProfileViewModel - Updated user profile from server: $userProfile")
                } else {
                    LogUtils.e("ProfileViewModel - getUserProfile failure: Failed to get user profile")
                    // 使用本地缓存的用户信息
                    _uiState.update { it.copy(userProfile = UserProfileManager.getUserProfile()) }
                }
            } catch (e: Exception) {
                LogUtils.e("ProfileViewModel - getUserProfile exception: ${e.message}")
                // 使用本地缓存的用户信息
                _uiState.update { it.copy(userProfile = UserProfileManager.getUserProfile()) }
            }
        }
    }

    /** 更新用户信息（从本地） */
    fun updateUserInfoLocal() {
        _uiState.update { it.copy(userProfile = UserProfileManager.getUserProfile()) }
    }

    /** 获取用户创建的 Agents 列表（从网络加载） */
    fun getUserCreatedAgents() {
        currentPage = 0
        hasMore = true

        // 清空列表并加载数据
        _uiState.update {
            it.copy(
                userCreatedAgents = emptyList(),
                isLoading = false,
                error = null
            )
        }
        loadUserCreatedAgents()
    }

    /** 从缓存加载用户创建的 Agents 列表 */
    fun loadUserCreatedAgentsFromCache() {
        val cachedAgents = AgentCacheManager.getCachedUserCreatedAgents()
        if (cachedAgents.isNotEmpty()) {
            _uiState.update { it.copy(userCreatedAgents = cachedAgents) }
            LogUtils.i("ProfileViewModel - 从缓存加载用户自建agents: ${cachedAgents.size}个")
        }
    }

    /** 加载更多用户创建的 Agents */
    fun loadMoreUserCreatedAgents() {
        if (!_uiState.value.isLoading && hasMore) {
            currentPage++
            loadUserCreatedAgents()
        } else {
            LogUtils.d(
                "ProfileViewModel - loadMoreUserCreatedAgents - 跳过加载: isLoading=${_uiState.value.isLoading}, hasMore=$hasMore"
            )
        }
    }


    /** 加载用户创建的 Agents 列表 */
    private fun loadUserCreatedAgents() {
        if (_uiState.value.isLoading) return // 防止并发加载

        // 检查登录状态，确保有有效的token后再调用需要认证的接口
        if (!IntySetting.isLogin() || IntySetting.getCurToken().isEmpty()) {
            LogUtils.w("ProfileViewModel - 用户未登录或token无效，跳过用户自建agents加载")
            _uiState.update { it.copy(isLoading = false, error = "User not logged in") }
            return
        }

        _uiState.update { it.copy(isLoading = true, error = null) }
        val skip = currentPage * PAGE_SIZE

        viewModelScope.launch(Dispatchers.IO) {
            try {
                val result = agentApi.getUserCreatedAgents(skip, PAGE_SIZE)

                when (result) {
                    is HttpResult.Success -> {
                        if (result.data.isEmpty()) {
                            hasMore = false
                            _uiState.update { it.copy(hasMore = false) }
                        } else {
                            _uiState.update { current ->
                                if (currentPage == 0) {
                                    // 第一页，直接替换并更新缓存
                                    AgentCacheManager.cacheUserCreatedAgents(result.data)
                                    current.copy(userCreatedAgents = result.data, hasMore = true)
                                } else {
                                    // 后续页，追加到现有列表
                                    current.copy(
                                        userCreatedAgents = current.userCreatedAgents + result.data,
                                        hasMore = true
                                    )
                                }
                            }
                            LogUtils.i(
                                "ProfileViewModel - loadUserCreatedAgents - ${if (currentPage == 0) "替换" else "追加"}第${currentPage + 1}页数据: ${result.data.size}个"
                            )
                        }
                    }

                    is HttpResult.Failure -> {
                        LogUtils.e("ProfileViewModel - loadUserCreatedAgents - API failure: ${result.message}")
                        _uiState.update { it.copy(error = result.message) }
                        // If loading failed, rollback page counter
                        if (currentPage > 0) {
                            currentPage--
                            LogUtils.i("ProfileViewModel - loadUserCreatedAgents - 页码回退到: $currentPage")
                        }
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("ProfileViewModel - loadUserCreatedAgents exception: ${e.message}")
                _uiState.update { it.copy(error = e.message) }
                // If loading failed, rollback page counter
                if (currentPage > 0) {
                    currentPage--
                    LogUtils.i("ProfileViewModel - loadUserCreatedAgents - 页码回退到: $currentPage")
                }
            } finally {
                _uiState.update { it.copy(isLoading = false) }
            }
        }
    }

    /** 刷新用户创建的 Agents 列表（强制从网络加载） */
    fun refreshCreatedAgents() {
        // 如果已经在加载中，避免重复请求
        if (!_uiState.value.isLoading) {
            getUserCreatedAgents()
        } else {
            LogUtils.i("ProfileViewModel - refreshCreatedAgents - 跳过刷新，正在加载中")
        }
    }

    /** 删除 Agent */
    fun deleteAgent(agentId: String, onSuccess: () -> Unit, onError: (String) -> Unit) {
        launchBackground {
            try {
                val result = agentApi.deleteAgent(agentId)

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            // 从用户创建的角色列表中移除
                            _uiState.update { current ->
                                current.copy(
                                    userCreatedAgents = current.userCreatedAgents.filter { it.id != agentId }
                                )
                            }

                            // 同步更新缓存
                            AgentCacheManager.removeAgent(agentId)

                            ToastUtils.showShort(R.string.character_deleted_successfully)
                            onSuccess()
                        }

                        is HttpResult.Failure -> {
                            val errorMessage =
                                result.message.ifBlank {
                                    Utils.getApp()
                                        .getString(
                                            R.string.operation_failed_check_network,
                                            Utils.getApp().getString(R.string.delete_failed),
                                            Utils.getApp()
                                                .getString(R.string.check_network_connection),
                                        )
                                }
                            ToastUtils.showShort(
                                Utils.getApp()
                                    .getString(R.string.delete_failed_with_reason, errorMessage)
                            )
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: HttpException) {
                LogUtils.e("ProfileViewModel - deleteAgent HTTP Exception: ${e.code()} - ${e.message()}")
                val errorMessage = HttpErrorHandler.handleHttpException(e, "delete")
                withContext(Dispatchers.Main) {
                    ToastUtils.showShort(errorMessage)
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                LogUtils.e("ProfileViewModel - deleteAgent exception: ${e.message}")
                val errorMessage = HttpErrorHandler.handleGeneralException(e, "delete")
                withContext(Dispatchers.Main) {
                    ToastUtils.showShort(errorMessage)
                    onError(errorMessage)
                }
            }
        }
    }

    /** 跟踪页面访问 */
    fun trackPageView(contextName: String) {
        PageTrackingHelper.trackPageView(
            "ProfilePage",
            contextName,
            mapOf(
                "agent_count" to _uiState.value.userCreatedAgents.size,
                "is_loading" to _uiState.value.isLoading,
            )
        )
    }

    /** 清空所有数据（用于用户登出等场景） */
    fun clearAllData() {
        _uiState.update { ProfileUiState() }
        currentPage = 0
        hasMore = true
    }
}
