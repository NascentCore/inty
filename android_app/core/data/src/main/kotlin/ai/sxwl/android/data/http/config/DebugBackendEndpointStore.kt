package ai.sxwl.android.data.http.config

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context

/**
 * 用来存储全局的后端地址信息，debug build 下运行时切换后端地址。
 */
object DebugBackendEndpointStore {

    private const val PREF_NAME = "debug_network_config"
    private const val KEY_BASE_URL = "override_base_url"

    private val prefs by lazy {
        Utils.getApp().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    }

    data class OverrideInfo(val url: String)

    fun isRuntimeOverrideSupported(
        buildType: NetworkConfig.BuildType = NetworkConfig.getCurrentBuildType(),
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

        prefs
            .edit()
            .putString(KEY_BASE_URL, url)
            .apply()

        LogUtils.i("DebugBackendEndpointStore", "Runtime backend updated to $url")
        return OverrideInfo(url)
    }

    fun clearOverride() {
        if (!prefs.contains(KEY_BASE_URL)) return
        prefs.edit().remove(KEY_BASE_URL).apply()
        LogUtils.i("DebugBackendEndpointStore", "Runtime backend override cleared")
    }

}
