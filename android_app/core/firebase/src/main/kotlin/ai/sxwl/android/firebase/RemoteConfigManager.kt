package ai.sxwl.android.firebase

import ai.sxwl.android.utils.AppUtils
import ai.sxwl.android.utils.LogUtils
import android.content.Context
import com.google.firebase.remoteconfig.FirebaseRemoteConfig
import com.google.firebase.remoteconfig.FirebaseRemoteConfigSettings
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

/**
 * Remote Config 管理器：封装初始化、默认值与参数访问
 * 用于最小化演示：A/B 实验 + 头像大小限制
 */
object RemoteConfigManager {

    private const val KEY_AB_HOME_BANNER_VARIANT = "ab_home_banner_variant" // "A" | "B"
    private const val KEY_AVATAR_MAX_SIZE_MB = "avatar_max_size_mb" // Int (MB)

    private val ioScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    @Volatile private var remoteConfig: FirebaseRemoteConfig? = null

    private val _abVariant = MutableStateFlow("A")
    val abVariant: StateFlow<String> = _abVariant

    fun initialize(context: Context) {
        if (remoteConfig != null) return

        try {
            val rc = FirebaseRemoteConfig.getInstance()
            val settings =
                FirebaseRemoteConfigSettings.Builder()
                    .setMinimumFetchIntervalInSeconds(
                        if (AppUtils.isAppDebug()) 0 else 12 * 60 * 60,
                    )
                    .build()
            rc.setConfigSettingsAsync(settings)

            // 设置默认值，保证首次启动也有稳定的行为
            val defaults = mapOf(
                KEY_AB_HOME_BANNER_VARIANT to "A",
                KEY_AVATAR_MAX_SIZE_MB to 10L,
            )
            rc.setDefaultsAsync(defaults)

            remoteConfig = rc

            // 异步拉取一次，激活并更新内存态
            refreshAsync()
        } catch (e: Exception) {
            LogUtils.e("RemoteConfigManager - 初始化失败: ${e.message}")
        }
    }

    fun refreshAsync() {
        val rc = remoteConfig ?: return
        ioScope.launch {
            try {
                rc.fetchAndActivate().await()
                // 更新关键内存态
                _abVariant.value = rc.getString(KEY_AB_HOME_BANNER_VARIANT).ifEmpty { "A" }
                // 打点当前变体，便于观测
                FirebaseManager.logEvent(
                    "ab_home_banner_variant_updated",
                    mapOf("variant" to _abVariant.value),
                )
            } catch (e: Exception) {
                LogUtils.w("RemoteConfigManager - 刷新失败: ${e.message}")
            }
        }
    }

    fun getAbHomeBannerVariant(): String {
        val rc = remoteConfig ?: return _abVariant.value
        val value = rc.getString(KEY_AB_HOME_BANNER_VARIANT)
        return if (value.isNullOrEmpty()) _abVariant.value else value
    }

    fun getAvatarMaxSizeMb(): Int {
        val rc = remoteConfig ?: return 10
        val v = rc.getLong(KEY_AVATAR_MAX_SIZE_MB)
        return if (v <= 0) 10 else v.toInt()
    }
}
