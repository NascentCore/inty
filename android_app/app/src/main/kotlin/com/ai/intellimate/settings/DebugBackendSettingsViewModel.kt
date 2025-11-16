package com.ai.intellimate.settings

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.http.IntyNetworkManager
import ai.sxwl.android.data.http.config.Constant
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore.OverrideInfo
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.ViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

private const val TAG = "DebugBackendSettings"

class DebugBackendSettingsViewModel : ViewModel() {

    data class UiState(
        val isSupported: Boolean,
        val buildType: String,
        val activeBaseUrl: String,
        val overrideInfo: OverrideInfo?,
    ) {
        val hasOverride: Boolean = overrideInfo != null
    }

    val quickPresets =
        listOf(
            "Dev" to "https://${Constant.USER_HOST_DEV}/",
            "Prod" to "https://${Constant.USER_HOST}/",
            "Local" to "http://${Constant.USER_HOST_LOCAL}/",
        )

    private val _uiState = MutableStateFlow(createInitialState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    private fun createInitialState(): UiState {
        val overrideInfo = DebugBackendEndpointStore.getOverrideInfo()
        val activeBaseUrl = NetworkConfig.getBaseUrl()
        return UiState(
            isSupported = DebugBackendEndpointStore.isRuntimeOverrideSupported(),
            buildType = NetworkConfig.getCurrentBuildType().value,
            activeBaseUrl = activeBaseUrl,
            overrideInfo = overrideInfo,
        )
    }

    fun applyPreset(url: String) {
        val normalized = DebugBackendEndpointStore.normalizeAndValidate(url)
        if (normalized == null) {
            LogUtils.e(TAG, "Invalid preset URL: $url")
            return
        }

        val info =
            runCatching { DebugBackendEndpointStore.persistOverride(url) }
                .onFailure { LogUtils.e(TAG, "Failed to persist runtime backend override", it) }
                .getOrElse { return }

        // 清除 Inty SDK 和 Retrofit 的客户端缓存
        IntyNetworkManager.clearClientCache()
        NetServiceMgr.clearCache()

        _uiState.update {
            it.copy(
                activeBaseUrl = NetworkConfig.getBaseUrl(),
                overrideInfo = info,
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
                overrideInfo = null,
            )
        }
    }
}
