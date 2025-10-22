package ai.sxwl.android.design.ui

import ai.sxwl.android.design.R
import ai.sxwl.android.design.emptyInteractionSource
import ai.sxwl.android.design.isInPreview
import androidx.annotation.DrawableRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage

/**
 * 简单封装的compose的topAppBar
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HeartTopAppBar(
    modifier: Modifier = Modifier,//修饰符
    title: String = "",//标题
    @DrawableRes navIcon: Int? = R.drawable.ic_arrow_back,//导航图标
    @DrawableRes moreIcon: Int? = null,
    onClickMore: () -> Unit = {},//点击设置按钮
    onBack: () -> Unit = {},//返回按钮的事件
) {
    TopAppBar(
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (title.isNotEmpty()) {
                    Text(
                        text = title,
                        fontSize = 20.sp,
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold
                    )
                }

            }
        },
        modifier = modifier,
        navigationIcon = {
            IconButton(onClick = onBack, enabled = navIcon != null) {
                navIcon?.let {
                    Icon(
                        painter = painterResource(navIcon),
                        contentDescription = "",
                        tint = Color.White
                    )
                }
            }
        },
        actions = {
            IconButton(onClick = onClickMore, enabled = moreIcon != null) {
                moreIcon?.let {
                    Icon(
                        painter = painterResource(moreIcon),
                        contentDescription = "",
                        tint = Color.White
                    )
                }
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent)
    )
}

/**
 * 效果预览
 */
@Preview
@Composable
private fun 预览普通封装的状态栏() {
    Column(modifier = Modifier.fillMaxWidth()) {
        HeartTopAppBar(title = "IntelliMate") { }
        Spacer(Modifier.height(8.dp))
        HeartTopAppBar(title = "", navIcon = null, moreIcon = R.drawable.ic_settings) { }
        HeartTopAppBar(
            title = "",
            navIcon = R.drawable.ic_arrow_back,
            moreIcon = R.drawable.ic_more
        ) { }
    }
}

/**
 * 简单封装的compose的topAppBar
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HeartStarTopAppBar(
    modifier: Modifier = Modifier,//修饰符
    title: String = "",//标题
) {
    TopAppBar(
        title = {
            Text(
                text = buildAnnotatedString {
                    withStyle(
                        style = SpanStyle(brush = primaryBtnBrush)
                    ) {
                        append(title)
                    }
                },
                fontSize = 24.sp,
                lineHeight = 28.sp,
                fontWeight = FontWeight.Black
            )
        },
        modifier = modifier,
        colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent)
    )
}

/**
 * 效果预览
 */
@Preview
@Composable
private fun 预览star标题的状态栏() {
    Column(modifier = Modifier.fillMaxWidth()) {
        HeartStarTopAppBar(title = "✨Popular")
    }
}

/**
 * 与Ai聊天顶部的标题栏
 */
data class HeartChatTopAppBarData(
    val avatarUrl: String? = "",//头像的url
    val nickName: String? = "",//昵称
    val hasFollowed: Boolean = false,//是否已经关注
)

/**
 * 和ai聊天顶部的标题栏
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HeartChatTopAppBar(
    modifier: Modifier = Modifier,
    showBack: Boolean = false,//是否显示返回按钮
    onBack: () -> Unit = {},//点击返回
    chatTopData: HeartChatTopAppBarData,//相关数据
    onBarClick: () -> Unit = {},//点击用户头像昵称区域
    onAddClick: () -> Unit = {},//点击加号
    onMenuClick: () -> Unit = {},//点击右侧菜单
) {
    TopAppBar(
        title = {
            Row(
                modifier = Modifier
                    .height(40.dp)
                    .clip(RoundedCornerShape(20.dp))
                    .background(color = Color.Black.copy(.4f))
                    .clickable(onClick = onBarClick)
                    .padding(horizontal = 2.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                val avatar = if (isInPreview) R.drawable.img_girl_lite else chatTopData.avatarUrl
                AsyncImage(
                    model = avatar,
                    contentDescription = "avatar",
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape),
                    contentScale = ContentScale.Crop
                )

                val nickName = if (isInPreview) "Emma Ai Bot" else chatTopData.nickName ?: ""

                Text(
                    text = nickName,
                    fontSize = 14.sp,
                    lineHeight = 22.sp,
                    fontWeight = FontWeight.Medium,
                    color = Color.White,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.widthIn(min = 20.dp, max = 70.dp)
                )

                if (!(chatTopData.hasFollowed)) {
                    IconButton(onClick = onAddClick, modifier = Modifier.size(20.dp)) {
                        Icon(
                            painter = painterResource(R.drawable.ic_plus_circle),
                            contentDescription = "关注",
                            tint = Color.White,
                        )
                    }
                    Spacer(Modifier.width(8.dp))
                } else {
                    IconButton(onClick = onAddClick, modifier = Modifier.size(20.dp)) {
                        Icon(
                            painter = painterResource(R.drawable.ic_heart_filled),
                            contentDescription = "已关注",
                            tint = Color(0xFFFF6B6B),
                        )
                    }
                    Spacer(Modifier.width(8.dp))
                }
            }
        },
        modifier = modifier,
        navigationIcon = {
            if (showBack) {
                IconButton(onClick = onBack) {
                    Icon(
                        painter = painterResource(R.drawable.ic_arrow_back),
                        contentDescription = "",
                        tint = Color.White
                    )
                }
            }

        },
        actions = {
            Box(
                modifier = Modifier
                    .size(48.dp, 32.dp)
                    .clip(RoundedCornerShape(topStart = 16.dp, bottomStart = 16.dp))
                    .background(
                        Color.Black.copy(.4f),
                        shape = RoundedCornerShape(topStart = 16.dp, bottomStart = 16.dp)
                    )
                    .clickable(onClick = onMenuClick),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    painter = painterResource(R.drawable.ic_top_right_menu),
                    contentDescription = "",
                    tint = Color.White,
                    modifier = Modifier.size(20.dp)
                )
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent)
    )
}

@Preview
@Composable
private fun 预览聊天顶部标题栏() {
    HeartChatTopAppBar(
        modifier = Modifier.background(Color.White),
        chatTopData = HeartChatTopAppBarData()
    )
}

/**
 * 带Tab的顶部工具栏
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HeartTabTopAppBar(
    modifier: Modifier = Modifier,
    tabs: List<String> = listOf("Message", "Following"),
    selectedTabIndex: Int = 0,
    onTabSelected: (Int) -> Unit = {},
) {

    CenterAlignedTopAppBar(
        title = {
            TabRow(
                selectedTabIndex = selectedTabIndex,
                modifier = Modifier.width(240.dp), // 进一步限制TabRow宽度，让tab更紧凑
                containerColor = Color.Transparent,
                indicator = { tabPositions ->
                    // 使用自定义的indicator，跟随tab移动
                    if (tabPositions.isNotEmpty()) {
                        Box(
                            modifier = Modifier
                                .offset(
                                    x = tabPositions[selectedTabIndex].left,
                                    y = 0.dp
                                ),
                            contentAlignment = Alignment.BottomStart
                        ) {
                            Image(
                                painter = painterResource(R.drawable.icon_indicator_messages),
                                contentDescription = "",
                                modifier = Modifier.width(tabPositions[selectedTabIndex].width)
                            )
                        }
                    }
                },
                divider = {} // 移除默认分割线
            ) {
                tabs.forEachIndexed { index, tabTitle ->
                    Tab(
                        selected = selectedTabIndex == index,
                        onClick = { onTabSelected(index) },
                        interactionSource = remember { emptyInteractionSource },
                        text = {
                            if (selectedTabIndex == index) {
                                // 选中状态使用渐变色文字
                                Text(
                                    text = buildAnnotatedString {
                                        withStyle(
                                            style = SpanStyle(brush = primaryBtnBrush)
                                        ) {
                                            append(tabTitle)
                                        }
                                    },
                                    fontSize = 20.sp,
                                    lineHeight = 28.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    textAlign = TextAlign.Center,
                                )
                            } else {
                                // 未选中状态使用白色
                                Text(
                                    text = tabTitle,
                                    fontSize = 20.sp,
                                    lineHeight = 28.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = Color.White,
                                    textAlign = TextAlign.Center,
                                )
                            }
                        }
                    )
                }
            }
        },
        modifier = modifier,
        colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent)
    )
}

@Preview
@Composable
private fun 预览TabLayout() {
    Column {
        var checkedIndex by remember { mutableIntStateOf(0) }
        HeartTabTopAppBar(
            tabs = listOf("Message", "Following"),
            selectedTabIndex = checkedIndex,
            onTabSelected = { checkedIndex = it },
        )

        Spacer(modifier = Modifier.height(16.dp))

        // 展示自定义tabs的使用
        var customCheckedIndex by remember { mutableIntStateOf(0) }
        HeartTabTopAppBar(
            tabs = listOf("推荐", "关注", "最新"),
            selectedTabIndex = customCheckedIndex,
            onTabSelected = { customCheckedIndex = it },
        )
    }
}


@Preview
@Composable
fun HeartTopAppBarBackground(modifier: Modifier = Modifier) {
    //背景图
    Image(
        painter = painterResource(R.drawable.img_profile_bg_top),
        contentDescription = "",
        contentScale = ContentScale.Crop,
        modifier = modifier
    )
}

@Preview
@Composable
private fun 预览头像裁剪() {
    HeartTopAppBar(
        title = "裁剪头像",
        navIcon = R.drawable.ic_delete,
        moreIcon = R.drawable.ic_done,
        onClickMore = {},
        onBack = {}
    )
}
