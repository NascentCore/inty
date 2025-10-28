package ai.sxwl.android.design

import androidx.compose.runtime.Composable
import androidx.compose.runtime.Stable
import androidx.compose.ui.platform.LocalInspectionMode
import androidx.compose.ui.platform.LocalView

// 用于标记，当前代码适用于IDE预览，还是实际代码环境
@Stable
val isInPreview
    @Composable get() = LocalInspectionMode.current

@Stable
val isInEditMode: Boolean
    @Composable get() = LocalView.current.isInEditMode
