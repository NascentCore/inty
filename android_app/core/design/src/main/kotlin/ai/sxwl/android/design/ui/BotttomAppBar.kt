package ai.sxwl.android.design.ui

import ai.sxwl.android.design.theme.HeartColor
import androidx.annotation.IntRange
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ai.sxwl.android.design.R

/**
 * 封装项目用的Bottom Navigation Bar
 */
@Composable
fun HeartBottomAppBar(
    modifier: Modifier = Modifier,
    selectedTab: Int = 0,
    tabItems: List<HeartBottomTabItem> = bottomTabItems,
    onTabSelected: (Int) -> Unit = {},
) {

    NavigationBar(
        modifier = modifier.fillMaxWidth(),
        containerColor = HeartColor.primaryColor,
        tonalElevation = 8.dp
    ) {
        tabItems.forEach { tab ->
            val isSelected = selectedTab == tab.index
            val iconRes = if (isSelected) tab.selectedIcon else tab.unselectedIcon

            NavigationBarItem(
                selected = isSelected,
                onClick = {
                    onTabSelected(tab.index)
                },
                icon = {
                    Box(modifier = Modifier) {
                        Image(
                            painter = painterResource(id = iconRes),
                            contentDescription = null,
                            modifier = Modifier.size(24.dp),
                        )
                        if (tab.hasRedDot) HeartRedDot(Modifier.align(Alignment.TopEnd))
                    }

                },
                colors = NavigationBarItemDefaults.colors(indicatorColor = Color.Transparent)
            )
        }
    }
}

/**
 * 项目底部tab数据
 */
data class HeartBottomTabItem(
    val index: Int,
    val selectedIcon: Int,
    val unselectedIcon: Int,
    val hasRedDot: Boolean = false,//是否有红点
)

private val bottomTabItems = listOf(
    HeartBottomTabItem(
        index = 0,
        selectedIcon = R.drawable.ic_tab_chat_selected,
        unselectedIcon = R.drawable.ic_tab_chat_unselected,
    ),
    HeartBottomTabItem(
        index = 1,
        selectedIcon = R.drawable.ic_tab_notification_selected,
        unselectedIcon = R.drawable.ic_tab_notification_unselected,
        hasRedDot = true
    ),
    HeartBottomTabItem(
        index = 2,
        selectedIcon = R.drawable.ic_tab_ai,
        unselectedIcon = R.drawable.ic_tab_ai,
    ),
    HeartBottomTabItem(
        index = 3,
        selectedIcon = R.drawable.ic_tab_recommend_selected,
        unselectedIcon = R.drawable.ic_tab_recommend_unselected,
    ),
    HeartBottomTabItem(
        index = 4,
        selectedIcon = R.drawable.ic_tab_profile_selected,
        unselectedIcon = R.drawable.ic_tab_profile_unselected,
    )
)

@Preview
@Composable
private fun 预览底部导航栏() {

    Column(
        modifier = Modifier.Companion.background(HeartColor.primaryColor)
    ) {
        var checkedIndex by remember { mutableIntStateOf(0) }
        HeartBottomAppBar(
            modifier = Modifier.fillMaxWidth(),
            selectedTab = checkedIndex,
            tabItems = bottomTabItems
        ) { checkedIndex = it }
    }
}

@Preview
@Composable
fun HeartRedDot(modifier: Modifier = Modifier, radius: Int = 8) {
    Box(
        modifier = modifier
            .size(radius.dp)
            .clip(CircleShape)
            .background(Color.Red)
    )
}

/**
 * 红点数字的现实，可以配置 99+，或者完整显示，目前基于业务，数字必须>0
 */
@Composable
fun HeartRedNum(
    modifier: Modifier = Modifier,
    @IntRange(from = 0) num: Int,
    omit: Boolean = false,
) {

    val numberStr = when {
        num in 1..99 -> "$num"
        num > 99 -> if (omit) "99+" else "$num"
        else -> ""
    }

    if (numberStr.isNotBlank()) {
        Box(
            modifier = modifier
                .sizeIn(minWidth = 12.dp, minHeight = 12.dp)
                .clip(CircleShape)
                .background(Color.Red)
                .padding(horizontal = 2.dp, vertical = 1.dp),
            contentAlignment = Alignment.Center
        ) {

            Text(
                text = numberStr, fontSize = 10.sp,
                fontWeight = FontWeight.Normal, color = Color.White,
                textAlign = TextAlign.Center
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
