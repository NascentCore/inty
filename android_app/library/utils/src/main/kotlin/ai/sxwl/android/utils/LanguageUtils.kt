package ai.sxwl.android.utils

import android.content.Context
import android.content.res.Configuration
import android.content.res.Resources
import android.os.Build
import android.util.Log
import java.util.IllformedLocaleException
import java.util.Locale

/** 语言工具类 提供语言相关的工具方法 */
object LanguageUtils {

    private const val KEY_LOCALE = "KEY_LOCALE"
    private const val VALUE_FOLLOW_SYSTEM = "VALUE_FOLLOW_SYSTEM"

    /** 应用系统语言 */
    fun applySystemLanguage() {
        applySystemLanguage(false)
    }

    /** 应用系统语言 */
    fun applySystemLanguage(isRelaunchApp: Boolean) {
        applyLanguageReal(null, isRelaunchApp)
    }

    /** 应用语言 */
    fun applyLanguage(locale: Locale) {
        applyLanguage(locale, false)
    }

    /** 应用语言 */
    fun applyLanguage(locale: Locale, isRelaunchApp: Boolean) {
        applyLanguageReal(locale, isRelaunchApp)
    }

    /** 获取当前语言 */
    fun getCurrentLanguage(): Locale {
        return try {
            val app = runCatching { Utils.getApp() }.getOrNull()
            if (app != null) {
                getCurrentLanguage(app)
            } else {
                Log.w("LanguageUtils", "App context is null, using default locale")
                Locale.getDefault()
            }
        } catch (e: Exception) {
            Log.e("LanguageUtils", "Failed to get current language", e)
            Locale.getDefault()
        }
    }

    /** 获取当前语言 */
    fun getCurrentLanguage(context: Context): Locale {
        return try {
            val resources = context.resources
            val configuration = resources.configuration
            getLocale(configuration)
        } catch (e: Exception) {
            Log.e("LanguageUtils", "Failed to get current language", e)
            Locale.getDefault()
        }
    }

    /** 获取系统语言 */
    fun getSystemLanguage(): Locale {
        return try {
            getLocale(Resources.getSystem().configuration)
        } catch (e: Exception) {
            Log.e("LanguageUtils", "Failed to get system language", e)
            Locale.getDefault()
        }
    }

    /** 是否为中文 */
    fun isChinese(): Boolean {
        return isChinese(getCurrentLanguage())
    }

    /** 是否为中文 */
    fun isChinese(locale: Locale): Boolean {
        return locale.language == "zh"
    }

    /** 是否为英文 */
    fun isEnglish(): Boolean {
        return isEnglish(getCurrentLanguage())
    }

    /** 是否为英文 */
    fun isEnglish(locale: Locale): Boolean {
        return locale.language == "en"
    }

    /** 获取语言字符串 */
    fun locale2String(locale: Locale): String {
        return "${locale.language}_${locale.country}"
    }

    /** 字符串转语言 */
    fun string2Locale(localeString: String?): Locale? {
        if (localeString.isNullOrEmpty()) return null
        return try {
            val parts = localeString.split("_").filter { it.isNotBlank() }
            if (parts.isEmpty()) {
                Log.w("LanguageUtils", "Locale string is empty after split: $localeString")
                return null
            }
            val builder = Locale.Builder().setLanguage(parts[0])
            if (parts.size >= 2) {
                builder.setRegion(parts[1])
            }
            if (parts.size >= 3) {
                builder.setVariant(parts[2])
            }
            builder.build()
        } catch (e: IllformedLocaleException) {
            Log.e("LanguageUtils", "Invalid locale arguments: $localeString", e)
            null
        } catch (e: Exception) {
            Log.e("LanguageUtils", "Failed to parse locale string: $localeString", e)
            null
        }
    }

    ///////////////////////////////////////////////////////////////////////////
    // private methods
    ///////////////////////////////////////////////////////////////////////////

    private fun applyLanguageReal(locale: Locale?, isRelaunchApp: Boolean) {
        // 简化实现，实际应用中需要保存到SharedPreferences
        val destLocal = locale ?: getSystemLanguage()
        updateAppContextLanguage(
            destLocal,
            object : Utils.Consumer<Boolean> {
                override fun accept(t: Boolean) {
                    if (t) {
                        restart(isRelaunchApp)
                    } else {
                        // 使用重启应用
                        AppUtils.relaunchApp()
                    }
                }
            },
        )
    }

    private fun restart(isRelaunchApp: Boolean) {
        if (isRelaunchApp) {
            AppUtils.relaunchApp()
        } else {
            try {
                val activityList = UtilsBridge.getActivityList()
                if (activityList.isEmpty()) {
                    Log.w("LanguageUtils", "No activities found, using app relaunch")
                    AppUtils.relaunchApp()
                    return
                }

                var successCount = 0
                for (activity in activityList) {
                    if (!activity.isFinishing && !activity.isDestroyed) {
                        try {
                            activity.recreate()
                            successCount++
                        } catch (e: IllegalStateException) {
                            Log.e(
                                "LanguageUtils",
                                "Activity is in invalid state: ${activity.javaClass.simpleName}",
                                e,
                            )
                        } catch (e: Exception) {
                            Log.e(
                                "LanguageUtils",
                                "Failed to recreate activity: ${activity.javaClass.simpleName}",
                                e,
                            )
                        }
                    }
                }

                if (successCount == 0) {
                    Log.w("LanguageUtils", "No activities were recreated, using app relaunch")
                    AppUtils.relaunchApp()
                }
            } catch (e: Exception) {
                Log.e("LanguageUtils", "Failed to get activity list", e)
                // 如果获取Activity列表失败，使用重启应用作为备选方案
                AppUtils.relaunchApp()
            }
        }
    }

    private fun updateAppContextLanguage(locale: Locale, consumer: Utils.Consumer<Boolean>) {
        try {
            val context = runCatching { Utils.getApp() }.getOrNull()
            if (context == null) {
                Log.e("LanguageUtils", "App context is null")
                consumer.accept(false)
                return
            }

            val configuration = Configuration(context.resources.configuration)
            configuration.setLocale(locale)

            try {
                val newContext = context.createConfigurationContext(configuration)
                consumer.accept(newContext != null)
            } catch (e: Exception) {
                Log.e("LanguageUtils", "Failed to create configuration context", e)
                consumer.accept(false)
            }
        } catch (e: Exception) {
            Log.e("LanguageUtils", "Failed to update app context language", e)
            consumer.accept(false)
        }
    }

    private fun getLocale(configuration: Configuration): Locale {
        return try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
                if (configuration.locales.isEmpty()) {
                    Log.w("LanguageUtils", "Configuration locales is empty, using default locale")
                    Locale.getDefault()
                } else {
                    configuration.locales[0]
                }
            } else {
                @Suppress("DEPRECATION") configuration.locale
            }
        } catch (e: Exception) {
            Log.e("LanguageUtils", "Failed to get locale from configuration", e)
            Locale.getDefault()
        }
    }
}
