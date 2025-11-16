package ai.sxwl.android.data.http.config

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.content.Context
import java.net.URI

/**
 * Runtime backend endpoint override store.
 *
 * This is only enabled for debug builds so QA can switch between dev / staging / local backends
 * without rebuilding the application.
 */
object DebugBackendEndpointStore {

    private const val PREF_NAME = "debug_network_config"
    private const val KEY_BASE_URL = "override_base_url"
    private const val KEY_UPDATED_AT = "override_base_url_updated_at"

    private val prefs by lazy {
        Utils.getApp().getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
    }

    data class OverrideInfo(val url: String, val updatedAt: Long)

    /**
     * Checks whether runtime overrides are allowed for the provided build type.
     */
    fun isRuntimeOverrideSupported(
        buildType: NetworkConfig.BuildType = NetworkConfig.getCurrentBuildType(),
    ): Boolean {
        return AppUtils.isAppDebug() && buildType == NetworkConfig.BuildType.DEBUG
    }

    /**
     * Returns the currently saved override (if any).
     */
    fun getOverrideInfo(): OverrideInfo? {
        if (!isRuntimeOverrideSupported()) return null
        val url = prefs.getString(KEY_BASE_URL, null)?.takeIf { it.isNotBlank() } ?: return null
        val updatedAt = prefs.getLong(KEY_UPDATED_AT, 0L)
        return OverrideInfo(url = url, updatedAt = updatedAt)
    }

    /**
     * Persists a new override. Input will be normalized and validated before saving.
     */
    fun persistOverride(rawInput: String): OverrideInfo {
        require(isRuntimeOverrideSupported()) {
            "Runtime backend override is only available for debug builds"
        }
        val normalized =
            normalizeAndValidate(rawInput)
                ?: throw IllegalArgumentException("Invalid backend url: $rawInput")

        val timestamp = System.currentTimeMillis()
        prefs
            .edit()
            .putString(KEY_BASE_URL, normalized)
            .putLong(KEY_UPDATED_AT, timestamp)
            .apply()

        LogUtils.i("DebugBackendEndpointStore", "Runtime backend updated to $normalized")
        return OverrideInfo(normalized, timestamp)
    }

    /**
     * Clears the current override (if it exists).
     */
    fun clearOverride() {
        if (!prefs.contains(KEY_BASE_URL)) return
        prefs.edit().remove(KEY_BASE_URL).remove(KEY_UPDATED_AT).apply()
        LogUtils.i("DebugBackendEndpointStore", "Runtime backend override cleared")
    }

    /**
     * Normalizes and validates the provided url string. Returns `null` when invalid.
     *
     * - Guarantees https:// scheme when absent
     * - Ensures trailing slash (Retrofit requirement)
     * - Rejects empty host / malformed input
     */
    fun normalizeAndValidate(rawInput: String): String? {
        val trimmed = rawInput.trim()
        if (trimmed.isEmpty()) return null

        val urlWithScheme =
            if (trimmed.startsWith("http://", ignoreCase = true) ||
                trimmed.startsWith("https://", ignoreCase = true)
            ) {
                trimmed
            } else {
                "https://$trimmed"
            }

        return runCatching {
            val uri = URI(urlWithScheme)
            if (uri.host.isNullOrBlank()) return@runCatching null

            val normalizedPath =
                when {
                    uri.path.isNullOrBlank() -> "/"
                    uri.path.endsWith("/") -> uri.path
                    else -> "${uri.path}/"
                }

            val normalizedUri =
                URI(uri.scheme, uri.userInfo, uri.host, uri.port, normalizedPath, null, null)
            normalizedUri.toString()
        }.onFailure {
            LogUtils.w("DebugBackendEndpointStore", "Failed to normalize url: ${it.message}")
        }.getOrNull()
    }
}
