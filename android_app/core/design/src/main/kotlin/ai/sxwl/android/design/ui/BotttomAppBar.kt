package ai.sxwl.android.design.ui

import ai.sxwl.android.design.R
import ai.sxwl.android.design.theme.HeartColor
import androidx.annotation.IntRange
import androidx.annotation.StringRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** 封装项目用的Bottom Navigation Bar */
@Composable
fun HeartBottomAppBar(
    modifier: Modifier = Modifier,
    selectedTab: Int = 0,
    tabItems: List<HeartBottomTabItem> = bottomTabItems,
    iconSize: Dp = 24.dp,
    textSize: TextUnit = 12.sp,
    height: Dp? = null,
    labelSpacing: Dp = 4.dp,
    onTabSelected: (Int) -> Unit = {},
) {
    val navigationBarModifier =
        if (height != null) {
            modifier.fillMaxWidth().height(height)
        } else {
            modifier.fillMaxWidth()
        }

    NavigationBar(
        modifier = navigationBarModifier,
        containerColor = HeartColor.primaryColor,
        tonalElevation = 8.dp,
    ) {
        tabItems.forEach { tab ->
            val isSelected = selectedTab == tab.index
            val iconRes = if (isSelected) tab.selectedIcon else tab.unselectedIcon

            CompositionLocalProvider(
                LocalDensity provides
                    Density(
                        density = LocalDensity.current.density,
                        fontScale = 1f, // 核心：禁用字体缩放
                    )
            ) {
                NavigationBarItem(
                    selected = isSelected,
                    onClick = { onTabSelected(tab.index) },
                    icon = {
                        Box(modifier = Modifier) {
                            Image(
                                painter = painterResource(id = iconRes),
                                contentDescription = null,
                                modifier = Modifier.size(iconSize),
                            )
                            if (tab.hasRedDot) HeartRedDot(Modifier.align(Alignment.TopEnd))
                        }
                    },
                    label = {
                        val labelText =
                            when {
                                tab.labelResId != null -> stringResource(id = tab.labelResId)
                                tab.label.isNotEmpty() -> tab.label
                                else -> ""
                            }
                        if (labelText.isNotEmpty()) {
                            Text(
                                modifier = Modifier.padding(top = labelSpacing),
                                text = labelText,
                                fontSize = textSize,
                                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                color =
                                    if (isSelected) {
                                        BottomTabSelectedLabelColor
                                    } else {
                                        BottomTabUnselectedLabelColor
                                    },
                            )
                        }
                    },
                    colors = NavigationBarItemDefaults.colors(indicatorColor = Color.Transparent),
                )
            }
        }
    }
}

/** 项目底部tab数据 */
data class HeartBottomTabItem(
    val index: Int,
    val selectedIcon: Int,
    val unselectedIcon: Int,
    val label: String = "", // 标签文字（直接字符串）
    @StringRes val labelResId: Int? = null, // 标签文字资源 ID（支持国际化，优先级高于 label）
    val hasRedDot: Boolean = false, // 是否有红点
) {
    init {
        require(label.isEmpty() || labelResId == null) {
            "HeartBottomTabItem: label 和 labelResId 不能同时设置"
        }
    }
}

private val BottomTabSelectedLabelColor = Color(0xFF9C27B0)
private val BottomTabUnselectedLabelColor = Color(0x8C808080)

private val bottomTabItems =
    listOf(
        HeartBottomTabItem(
            index = 0,
            selectedIcon = R.drawable.ic_tab_chat_selected,
            unselectedIcon = R.drawable.ic_tab_chat_unselected,
            label = "聊天",
        ),
        HeartBottomTabItem(
            index = 1,
            selectedIcon = R.drawable.ic_tab_notification_selected,
            unselectedIcon = R.drawable.ic_tab_notification_unselected,
            label = "消息",
            hasRedDot = true,
        ),
        HeartBottomTabItem(
            index = 2,
            selectedIcon = R.drawable.ic_tab_ai,
            unselectedIcon = R.drawable.ic_tab_ai,
            label = "Create",
        ),
        HeartBottomTabItem(
            index = 3,
            selectedIcon = R.drawable.ic_tab_recommend_selected,
            unselectedIcon = R.drawable.ic_tab_recommend_unselected,
            label = "推荐",
        ),
        HeartBottomTabItem(
            index = 4,
            selectedIcon = R.drawable.ic_tab_profile_selected,
            unselectedIcon = R.drawable.ic_tab_profile_unselected,
            label = "我的",
        ),
    )

@Preview
@Composable
private fun 预览底部导航栏() {

    Column(modifier = Modifier.Companion.background(HeartColor.primaryColor)) {
        var checkedIndex by remember { mutableIntStateOf(0) }
        HeartBottomAppBar(
            modifier = Modifier.fillMaxWidth(),
            selectedTab = checkedIndex,
            tabItems = bottomTabItems,
        ) {
            checkedIndex = it
        }
    }
}

@Preview
@Composable
fun HeartRedDot(modifier: Modifier = Modifier, radius: Int = 8) {
    Box(modifier = modifier.size(radius.dp).clip(CircleShape).background(Color.Red))
}

/** 红点数字的现实，可以配置 99+，或者完整显示，目前基于业务，数字必须>0 */
@Composable
fun HeartRedNum(
    modifier: Modifier = Modifier,
    @IntRange(from = 0) num: Int,
    omit: Boolean = false,
) {

    val numberStr =
        when {
            num in 1..99 -> "$num"
            num > 99 -> if (omit) "99+" else "$num"
            else -> ""
        }

    if (numberStr.isNotBlank()) {
        Box(
            modifier =
                modifier
                    .sizeIn(minWidth = 12.dp, minHeight = 12.dp)
                    .clip(CircleShape)
                    .background(Color.Red)
                    .padding(horizontal = 2.dp, vertical = 1.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = numberStr,
                fontSize = 10.sp,
                fontWeight = FontWeight.Normal,
                color = Color.White,
                textAlign = TextAlign.Center,
            )
        }
    }
}

@Preview
@Composable
private fun 预览数字红点() {
    Row {
        HeartRedNum(num = 8)
        HeartRedNum(num = 998)
        HeartRedNum(num = 998, omit = true)
    }
}
