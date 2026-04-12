package com.ai.intellimate.settings

import ai.sxwl.android.data.http.NetworkStackCoordinator
import ai.sxwl.android.data.http.config.Constant
import ai.sxwl.android.data.http.config.DebugBackendEndpointStore
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

private const val TAG = "DebugBackendSettings"

private const val PRESET_NAME_LOCAL = "local"
private const val PRESET_NAME_DEV = "dev"
private const val PRESET_NAME_PROD = "prod"

class DebugBackendSettingsViewModel : ViewModel() {

    data class UiState(
        val buildType: String,
        val activeBaseUrl: String,
        val customUrlInput: String,
        val debugModeEnabled: Boolean,
        val remixButtonVisible: Boolean,
        val userTimeContextReportingEnabled: Boolean,
    )

    val quickPresets =
        listOf(
            PRESET_NAME_LOCAL to "http://${Constant.USER_HOST_LOCAL}/",
            PRESET_NAME_DEV to "https://${Constant.USER_HOST_DEV}/",
            PRESET_NAME_PROD to "https://${Constant.USER_HOST}/",
        )

    private val _uiState = MutableStateFlow(createInitialState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    init {
        val initialVisibility = getRemixButtonEffectiveVisibility()
        RemixButtonVisibilityManager.updateVisibility(initialVisibility)
    }

    private fun createInitialState(): UiState {
        val activeBaseUrl = NetworkConfig.getBaseUrl()
        val debugModeEnabled = AppUtils.isDebugMode()
        val remixButtonVisible = getRemixButtonEffectiveVisibility()
        val userTimeContextReportingEnabled =
            DebugBackendEndpointStore.getUserTimeContextReportingEnabled()
        return UiState(
            buildType = NetworkConfig.getCurrentBuildType().value,
            activeBaseUrl = activeBaseUrl,
            customUrlInput = "",
            debugModeEnabled = debugModeEnabled,
            remixButtonVisible = remixButtonVisible,
            userTimeContextReportingEnabled = userTimeContextReportingEnabled,
        )
    }

    private fun getRemixButtonEffectiveVisibility(): Boolean {
        val buildType = NetworkConfig.getCurrentBuildType()
        if (buildType == NetworkConfig.BuildType.RELEASE) {
            return false
        }
        val override = DebugBackendEndpointStore.getRemixButtonOverride()
        return override ?: true
    }

    fun applySelectedOverride(url: String) {
        runCatching { DebugBackendEndpointStore.persistOverride(url) }
            .onFailure { LogUtils.e(TAG, "Failed to persist runtime backend override", it) }
            .getOrElse {
                return
            }

        NetworkStackCoordinator.clearAllRuntimeCaches()

        _uiState.update { it.copy(activeBaseUrl = NetworkConfig.getBaseUrl(), customUrlInput = "") }
    }

    fun setCustomUrlInput(value: String) {
        _uiState.update { it.copy(customUrlInput = value) }
    }

    fun applyCustomUrl() {
        val url = _uiState.value.customUrlInput.trim()
        if (url.isBlank()) return
        val normalized = if (url.endsWith("/")) url else "$url/"
        applySelectedOverride(normalized)
    }

    fun resetOverride() {
        DebugBackendEndpointStore.clearOverride()
        NetworkStackCoordinator.clearAllRuntimeCaches()

        val active = NetworkConfig.getBaseUrl()
        _uiState.update { it.copy(activeBaseUrl = active, customUrlInput = "") }
    }

    fun toggleRemixButton() {
        val currentVisibility = _uiState.value.remixButtonVisible
        val newVisibility = !currentVisibility
        DebugBackendEndpointStore.persistRemixButtonOverride(newVisibility)
        _uiState.update { it.copy(remixButtonVisible = newVisibility) }
        RemixButtonVisibilityManager.updateVisibility(newVisibility)
    }

    fun resetRemixButtonOverride() {
        DebugBackendEndpointStore.clearRemixButtonOverride()
        val defaultVisibility = getRemixButtonEffectiveVisibility()
        _uiState.update { it.copy(remixButtonVisible = defaultVisibility) }
        RemixButtonVisibilityManager.updateVisibility(defaultVisibility)
    }

    fun setDebugModeEnabled(enabled: Boolean) {
        _uiState.update { it.copy(debugModeEnabled = enabled) }
        viewModelScope.launch {
            runCatching { AppUtils.setDebugMode(enabled) }
                .onFailure { error ->
                    LogUtils.e(TAG, "Failed to persist debug mode", error)
                    _uiState.update { it.copy(debugModeEnabled = AppUtils.isDebugMode()) }
                }
        }
    }

    fun toggleUserTimeContextReporting() {
        val current = _uiState.value.userTimeContextReportingEnabled
        val updated = !current
        DebugBackendEndpointStore.persistUserTimeContextReportingEnabled(updated)
        _uiState.update { it.copy(userTimeContextReportingEnabled = updated) }
    }
}

object RemixButtonVisibilityManager {
    private val _visibility = MutableStateFlow<Boolean?>(null)
    val visibility: StateFlow<Boolean?> = _visibility.asStateFlow()

    fun updateVisibility(visible: Boolean) {
        _visibility.value = visible
    }

    fun getCurrentVisibility(): Boolean {
        val buildType = NetworkConfig.getCurrentBuildType()
        if (buildType == NetworkConfig.BuildType.RELEASE) {
            return false
        }
        val override = DebugBackendEndpointStore.getRemixButtonOverride()
        return override ?: true
    }

    init {
        _visibility.value = getCurrentVisibility()
    }
}
