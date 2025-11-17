package com.ai.intellimate.settings

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.config.Constant
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

private const val TAG = "DebugBackendSettings"

private const val PRESET_NAME_LOCAL = "local"
private const val PRESET_NAME_DEV = "dev"
private const val PRESET_NAME_PROD = "prod"

class DebugBackendSettingsViewModel : ViewModel() {

    data class UiState(
        // 在配置页面中显示构建类型
        val buildType: String,
        // 当前生效的后端地址
        val activeBaseUrl: String,
    )

    val quickPresets =
        listOf(
            PRESET_NAME_LOCAL to "http://${Constant.USER_HOST_LOCAL}/",
            PRESET_NAME_DEV to "https://${Constant.USER_HOST_DEV}/",
            PRESET_NAME_PROD to "https://${Constant.USER_HOST}/",
        )

    private val _uiState = MutableStateFlow(createInitialState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private fun createInitialState(): UiState {
        val activeBaseUrl = NetworkConfig.getBaseUrl()
        return UiState(
            buildType = NetworkConfig.getCurrentBuildType().value,
            activeBaseUrl = activeBaseUrl,
        )
    }

    fun applyPreset(url: String) {
        runCatching { DebugBackendEndpointStore.persistOverride(url) }
            .onFailure { LogUtils.e(TAG, "Failed to persist runtime backend override", it) }
            .getOrElse { return }

        // 清除 Inty SDK 和 Retrofit 的客户端缓存
        IntyNetworkManager.clearClientCache()
        NetServiceMgr.clearCache()

        _uiState.update {
            it.copy(
                activeBaseUrl = NetworkConfig.getBaseUrl(),
            )
        }
    }

    fun resetOverride() {
        DebugBackendEndpointStore.clearOverride()
        // 清除 Inty SDK 和 Retrofit 的客户端缓存
        IntyNetworkManager.clearClientCache()
        NetServiceMgr.clearCache()

        val active = NetworkConfig.getBaseUrl()
        _uiState.update {
            it.copy(
                activeBaseUrl = active,
            )
        }
    }
}
