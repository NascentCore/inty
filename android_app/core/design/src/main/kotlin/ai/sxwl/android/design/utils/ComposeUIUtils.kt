package ai.sxwl.android.design.utils

import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.statusBars
import androidx.compose.foundation.layout.systemBars
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/** Compose UI工具类 用于获取系统bar高度、BottomBar和AppBar的高度 */
object ComposeUIUtils {
    /**
     * 获取状态栏高度
     *
     * @return 状态栏高度的Dp值
     */
    @Composable
    fun getStatusBarHeight(): Dp {
        val density = LocalDensity.current
        return with(density) { WindowInsets.statusBars.getTop(density).toDp() }
    }

    /**
     * 获取导航栏高度
     *
     * @return 导航栏高度的Dp值
     */
    @Composable
    fun getNavigationBarHeight(): Dp {
        val density = LocalDensity.current
        return with(density) { WindowInsets.navigationBars.getBottom(density).toDp() }
    }

    /**
     * 获取系统栏总高度（状态栏 + 导航栏）
     *
     * @return 系统栏总高度的Dp值
     */
    @Composable
    fun getSystemBarsHeight(): Dp {
        val density = LocalDensity.current
        return with(density) { WindowInsets.systemBars.getBottom(density).toDp() }
    }

    /**
     * 获取状态栏高度（像素值）
     *
     * @return 状态栏高度的像素值
     */
    @Composable
    fun getStatusBarHeightPx(): Int {
        return WindowInsets.statusBars.getTop(LocalDensity.current)
    }

    /**
     * 获取导航栏高度（像素值）
     *
     * @return 导航栏高度的像素值
     */
    @Composable
    fun getNavigationBarHeightPx(): Int {
        return WindowInsets.navigationBars.getBottom(LocalDensity.current)
    }

    /**
     * 获取系统栏总高度（像素值）
     *
     * @return 系统栏总高度的像素值
     */
    @Composable
    fun getSystemBarsHeightPx(): Int {
        return WindowInsets.systemBars.getBottom(LocalDensity.current)
    }

    /**
     * 获取BottomBar的标准高度 Material Design 3 中 BottomAppBar 的标准高度
     *
     * @return BottomBar高度的Dp值
     */
    @Composable
    fun getBottomBarHeight(): Dp {
        return 80.dp // Material Design 3 标准高度
    }

    /**
     * 获取TopAppBar的标准高度 Material Design 3 中 TopAppBar 的标准高度
     *
     * @return TopAppBar高度的Dp值
     */
    @Composable
    fun getTopAppBarHeight(): Dp {
        return 64.dp // Material Design 3 标准高度
    }

    /**
     * 获取Large TopAppBar的标准高度 Material Design 3 中 Large TopAppBar 的标准高度
     *
     * @return Large TopAppBar高度的Dp值
     */
    @Composable
    fun getLargeTopAppBarHeight(): Dp {
        return 152.dp // Material Design 3 标准高度
    }

    /**
     * 获取Medium TopAppBar的标准高度 Material Design 3 中 Medium TopAppBar 的标准高度
     *
     * @return Medium TopAppBar高度的Dp值
     */
    @Composable
    fun getMediumTopAppBarHeight(): Dp {
        return 112.dp // Material Design 3 标准高度
    }

    /**
     * 获取Small TopAppBar的标准高度 Material Design 3 中 Small TopAppBar 的标准高度
     *
     * @return Small TopAppBar高度的Dp值
     */
    @Composable
    fun getSmallTopAppBarHeight(): Dp {
        return 64.dp // Material Design 3 标准高度
    }

    /**
     * 获取屏幕安全区域的总高度 包括状态栏、导航栏等系统UI区域
     *
     * @return 安全区域总高度的Dp值
     */
    @Composable
    fun getSafeAreaHeight(): Dp {
        val density = LocalDensity.current
        return with(density) {
            val topInset = WindowInsets.statusBars.getTop(density)
            val bottomInset = WindowInsets.navigationBars.getBottom(density)
            (topInset + bottomInset).toDp()
        }
    }

    /**
     * 获取屏幕可用高度（排除系统bar）
     *
     * @return 可用高度的Dp值
     */
    @Composable
    fun getAvailableScreenHeight(): Dp {
        val density = LocalDensity.current
        return with(density) {
            val totalHeight = WindowInsets.systemBars.getBottom(density)
            val safeAreaHeight = getSafeAreaHeight().value
            (totalHeight - safeAreaHeight).dp
        }
    }
}
