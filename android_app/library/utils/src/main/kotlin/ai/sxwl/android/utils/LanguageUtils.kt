package ai.sxwl.android.utils

import android.content.Context
import android.content.res.Configuration
import android.content.res.Resources
import android.os.Build
import java.util.Locale

/**
 * 语言工具类
 * 提供语言相关的工具方法
 */
object LanguageUtils {

    private const val KEY_LOCALE = "KEY_LOCALE"
    private const val VALUE_FOLLOW_SYSTEM = "VALUE_FOLLOW_SYSTEM"

    /**
     * 应用系统语言
     */
    fun applySystemLanguage() {
        applySystemLanguage(false)
    }

    /**
     * 应用系统语言
     */
    fun applySystemLanguage(isRelaunchApp: Boolean) {
        applyLanguageReal(null, isRelaunchApp)
    }

    /**
     * 应用语言
     */
    fun applyLanguage(locale: Locale) {
        applyLanguage(locale, false)
    }

    /**
     * 应用语言
     */
    fun applyLanguage(locale: Locale, isRelaunchApp: Boolean) {
        applyLanguageReal(locale, isRelaunchApp)
    }

    /**
     * 获取当前语言
     */
    fun getCurrentLanguage(): Locale {
        return getCurrentLanguage(Utils.getApp())
    }

    /**
     * 获取当前语言
     */
    fun getCurrentLanguage(context: Context): Locale {
        val resources = context.resources
        val configuration = resources.configuration
        return getLocale(configuration)
    }

    /**
     * 获取系统语言
     */
    fun getSystemLanguage(): Locale {
        return getLocale(Resources.getSystem().configuration)
    }

    /**
     * 是否为中文
     */
    fun isChinese(): Boolean {
        return isChinese(getCurrentLanguage())
    }

    /**
     * 是否为中文
     */
    fun isChinese(locale: Locale): Boolean {
        return locale.language == "zh"
    }

    /**
     * 是否为英文
     */
    fun isEnglish(): Boolean {
        return isEnglish(getCurrentLanguage())
    }

    /**
     * 是否为英文
     */
    fun isEnglish(locale: Locale): Boolean {
        return locale.language == "en"
    }

    /**
     * 获取语言字符串
     */
    fun locale2String(locale: Locale): String {
        return "${locale.language}_${locale.country}"
    }

    /**
     * 字符串转语言
     */
    fun string2Locale(localeString: String?): Locale? {
        if (localeString.isNullOrEmpty()) return null
        val parts = localeString.split("_")
        return when (parts.size) {
            1 -> Locale(parts[0])
            2 -> Locale(parts[0], parts[1])
            else -> null
        }
    }

    ///////////////////////////////////////////////////////////////////////////
    // private methods
    ///////////////////////////////////////////////////////////////////////////

    private fun applyLanguageReal(locale: Locale?, isRelaunchApp: Boolean) {
        // 简化实现，实际应用中需要保存到SharedPreferences
        val destLocal = locale ?: getSystemLanguage()
        updateAppContextLanguage(destLocal, object : Utils.Consumer<Boolean> {
            override fun accept(success: Boolean) {
                if (success) {
                    restart(isRelaunchApp)
                } else {
                    // 使用重启应用
                    AppUtils.relaunchApp()
                }
            }
        })
    }

    private fun restart(isRelaunchApp: Boolean) {
        if (isRelaunchApp) {
            AppUtils.relaunchApp()
        } else {
            for (activity in UtilsBridge.getActivityList()) {
                activity.recreate()
            }
        }
    }

    private fun updateAppContextLanguage(locale: Locale, consumer: Utils.Consumer<Boolean>) {
        try {
            val context = Utils.getApp()
            val resources = context.resources
            val configuration = Configuration(resources.configuration)
            configuration.setLocale(locale)
            val newContext = context.createConfigurationContext(configuration)
            consumer.accept(true)
        } catch (e: Exception) {
            consumer.accept(false)
        }
    }

    private fun getLocale(configuration: Configuration): Locale {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            configuration.locales[0]
        } else {
            @Suppress("DEPRECATION")
            configuration.locale
        }
    }
}
