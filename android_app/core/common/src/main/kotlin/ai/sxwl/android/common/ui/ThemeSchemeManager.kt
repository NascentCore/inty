package ai.sxwl.android.common.ui

// CREATED_BY_AGENT

import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.theme.IntelliMateThemeScheme
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

private const val KEY_UI_THEME_SCHEME = "ui_theme_scheme"

/**
 * 全局 UI 主题方案管理器（支持运行时切换 + 持久化）。
 *
 * 设计说明：
 * - 使用 MMKV（通过 IntySetting 的 app-level 存储）持久化，避免引入额外依赖。
 * - 使用 StateFlow，确保 Compose 侧可以响应式刷新。
 */
object ThemeSchemeManager {
    private val _scheme = MutableStateFlow(loadPersistedScheme())
    val scheme: StateFlow<IntelliMateThemeScheme> = _scheme.asStateFlow()

    fun setScheme(scheme: IntelliMateThemeScheme) {
        if (_scheme.value == scheme) return
        _scheme.value = scheme
        IntySetting.setAppData(KEY_UI_THEME_SCHEME, scheme.name)
    }

    fun resetToDefault() {
        setScheme(IntelliMateThemeScheme.Default)
    }

    private fun loadPersistedScheme(): IntelliMateThemeScheme {
        val raw = IntySetting.getAppData(KEY_UI_THEME_SCHEME)?.trim().orEmpty()
        return runCatching { IntelliMateThemeScheme.valueOf(raw) }
            .getOrDefault(IntelliMateThemeScheme.Default)
    }
}

