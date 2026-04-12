package ai.sxwl.android.data.http.config

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context

/** 用来存储全局的后端地址信息，debug build 下运行时切换后端地址。 */
object DebugBackendEndpointStore {

    private const val PREF_NAME = "debug_network_config"
    private const val KEY_BASE_URL = "override_base_url"
    private const val KEY_REMIX_BUTTON_VISIBLE = "char_remix_button_visible"
    private const val KEY_USER_TIME_CONTEXT_REPORTING = "chat_user_time_context_reporting"

    private val prefs by lazy {
        Utils.getApp().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    }

    data class OverrideInfo(val url: String)

    fun isRuntimeOverrideSupported(
        buildType: NetworkConfig.BuildType = NetworkConfig.getCurrentBuildType()
    ): Boolean {
        return AppUtils.isAppDebug() && buildType == NetworkConfig.BuildType.DEBUG
    }

    fun getOverrideInfo(): OverrideInfo? {
        if (!isRuntimeOverrideSupported()) return null
        val url = prefs.getString(KEY_BASE_URL, null)?.takeIf { it.isNotBlank() } ?: return null
        return OverrideInfo(url = url)
    }

    fun persistOverride(rawInput: String): OverrideInfo {
        require(isRuntimeOverrideSupported()) {
            "Runtime backend override is only available for debug builds"
        }
        val url = rawInput.trim()

        prefs.edit().putString(KEY_BASE_URL, url).apply()

        LogUtils.i("DebugBackendEndpointStore", "Runtime backend updated to $url")
        return OverrideInfo(url)
    }

    fun clearOverride() {
        if (!prefs.contains(KEY_BASE_URL)) return
        prefs.edit().remove(KEY_BASE_URL).apply()
        LogUtils.i("DebugBackendEndpointStore", "Runtime backend override cleared")
    }

    fun getRemixButtonOverride(): Boolean? {
        if (!isRuntimeOverrideSupported()) return null
        if (!prefs.contains(KEY_REMIX_BUTTON_VISIBLE)) return null
        return prefs.getBoolean(KEY_REMIX_BUTTON_VISIBLE, true)
    }

    fun persistRemixButtonOverride(visible: Boolean) {
        require(isRuntimeOverrideSupported()) {
            "Runtime remix button override is only available for debug builds"
        }
        prefs.edit().putBoolean(KEY_REMIX_BUTTON_VISIBLE, visible).apply()
        LogUtils.i(
            "DebugBackendEndpointStore",
            "Runtime remix button visibility updated to $visible",
        )
    }

    fun clearRemixButtonOverride() {
        if (!prefs.contains(KEY_REMIX_BUTTON_VISIBLE)) return
        prefs.edit().remove(KEY_REMIX_BUTTON_VISIBLE).apply()
        LogUtils.i("DebugBackendEndpointStore", "Runtime remix button override cleared")
    }

    fun getUserTimeContextReportingEnabled(): Boolean {
        if (!isRuntimeOverrideSupported()) return false
        return prefs.getBoolean(KEY_USER_TIME_CONTEXT_REPORTING, true)
    }

    fun persistUserTimeContextReportingEnabled(enabled: Boolean) {
        require(isRuntimeOverrideSupported()) {
            "Runtime user time context override is only available for debug builds"
        }
        prefs.edit().putBoolean(KEY_USER_TIME_CONTEXT_REPORTING, enabled).apply()
        LogUtils.i(
            "DebugBackendEndpointStore",
            "Runtime user time context reporting updated to $enabled",
        )
    }

    fun clearUserTimeContextReportingOverride() {
        if (!prefs.contains(KEY_USER_TIME_CONTEXT_REPORTING)) return
        prefs.edit().remove(KEY_USER_TIME_CONTEXT_REPORTING).apply()
        LogUtils.i("DebugBackendEndpointStore", "Runtime user time context override cleared")
    }

}
