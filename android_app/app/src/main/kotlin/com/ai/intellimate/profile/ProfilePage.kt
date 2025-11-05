package com.ai.intellimate.profile

import ai.sxwl.android.common.analytics.PageTrackingHelper
import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.billing.VipStatus
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.AntiClick
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.utils.TimeUtils
import ai.sxwl.android.utils.ToastUtils
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import androidx.core.content.getSystemService
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.GridItemSpan
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.BiasAlignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.login.LoginActivity
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.vip.VipCenterActivity
import kotlinx.coroutines.launch
import kotlin.math.abs
import kotlin.math.min

/** "我的"页面 */
@Composable
internal fun ProfilePage(
    modifier: Modifier,
    userProfile: UserProfile,
    agents: List<AgentInfo>,
    onClickAgent: (AgentInfo) -> Unit,
    onEditAgent: ((AgentInfo) -> Unit)? = null,
    onDeleteAgent: ((AgentInfo) -> Unit)? = null,
    isLoading: Boolean = false,
    onLoadMore: () -> Unit = {},
    onShowSettings: () -> Unit,
) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val scope = rememberCoroutineScope()

    // 使用 PageTrackingHelper 进行页面跟踪
    LaunchedEffect(Unit) {
        PageTrackingHelper.trackPageView(
            "ProfilePage",
            "MainActivity",
            mapOf("agent_count" to agents.size, "is_loading" to isLoading)
        )
    }

    // 折叠相关状态
    val headerMaxHeight = 280.dp // Header 的完整高度
    val headerMinHeight = 80.dp // 折叠后的最小高度
    val maxCollapseOffset = with(density) { (headerMaxHeight - headerMinHeight).toPx() } // 最大折叠距离

    val collapseOffset = remember { Animatable(0f) }

    // 计算折叠比例 (0f = 完全展开, 1f = 完全折叠)
    val collapseProgress by remember {
        derivedStateOf {
            (collapseOffset.value / maxCollapseOffset).coerceIn(0f, 1f)
        }
    }

    // LazyGrid state - 需要在 nestedScrollConnection 之前创建
    val listState = rememberLazyGridState()

    // 嵌套滚动连接 - 处理折叠逻辑
    val nestedScrollConnection = remember(listState) {
        object : NestedScrollConnection {
            override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                // 向上滚动 (available.y < 0) - 优先折叠 header
                if (available.y < 0 && collapseOffset.value < maxCollapseOffset) {
                    val remainingToCollapse = maxCollapseOffset - collapseOffset.value
                    val toConsume = min(abs(available.y), remainingToCollapse)
                    scope.launch {
                        collapseOffset.snapTo(collapseOffset.value + toConsume)
                    }
                    // 返回消费的滚动量（负数表示向上滚动）
                    return Offset(0f, -toConsume)
                }

                // 向下滚动 (available.y > 0) - 优先展开 header
                if (available.y > 0 && collapseOffset.value > 0f) {
                    // 检查 LazyGrid 是否已经滚动到顶部
                    // 只有当 LazyGrid 在顶部时，才展开 header
                    if (listState.firstVisibleItemIndex == 0 &&
                        listState.firstVisibleItemScrollOffset == 0
                    ) {
                        val toConsume = min(available.y, collapseOffset.value)
                        scope.launch {
                            collapseOffset.snapTo(collapseOffset.value - toConsume)
                        }
                        // 返回消费的滚动量（正数表示向下滚动）
                        return Offset(0f, toConsume)
                    }
                }

                // 不消费滚动量，让 LazyGrid 处理
                return Offset.Zero
            }

            override suspend fun onPreFling(available: Velocity): Velocity {
                val currentVelocity = available.y

                // 向上滑动 - 继续折叠到完全折叠状态
                if (currentVelocity < 0 && collapseOffset.value < maxCollapseOffset) {
                    scope.launch {
                        collapseOffset.animateTo(
                            maxCollapseOffset,
                            animationSpec = tween(300)
                        )
                    }
                    // 消费部分速度，剩余速度传递给 LazyGrid
                    val remainingVelocity = Velocity(
                        0f,
                        currentVelocity * (1f - collapseProgress)
                    )
                    return remainingVelocity
                }

                // 向下滑动 - 继续展开到完全展开状态
                if (currentVelocity > 0 && collapseOffset.value > 0f) {
                    // 只有当 LazyGrid 在顶部时才展开
                    if (listState.firstVisibleItemIndex == 0 &&
                        listState.firstVisibleItemScrollOffset == 0
                    ) {
                        scope.launch {
                            collapseOffset.animateTo(
                                0f,
                                animationSpec = tween(300)
                            )
                        }
                        // 消费部分速度
                        val remainingVelocity = Velocity(
                            0f,
                            currentVelocity * collapseProgress
                        )
                        return remainingVelocity
                    }
                }

                // 不消费速度，让 LazyGrid 处理
                return Velocity.Zero
            }
        }
    }

    Box(modifier = modifier) {
        AsyncImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg,
            contentDescription = null
        )
        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Transparent),
            containerColor = Color.Transparent,
        ) { innerPadding ->
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .nestedScroll(nestedScrollConnection)
            ) {
                // Header 区域 - 可折叠
                ProfileHeader(
                    modifier = Modifier,
                    collapseProgress = collapseProgress,
                    userProfile = userProfile,
                    onShowSettings = onShowSettings,
                    innerPadding = innerPadding,
                    context = context,
                )

                // LazyGrid 区域
                if (agents.isEmpty()) {
                    Spacer(Modifier.height(48.dp))

                    AsyncImage(
                        modifier = Modifier.align(Alignment.CenterHorizontally),
                        model = R.drawable.img_content_empty,
                        contentDescription = null,
                    )

                    Spacer(Modifier.height(16.dp))

                    Text(
                        modifier =
                            Modifier
                                .padding(horizontal = 16.dp)
                                .align(Alignment.CenterHorizontally),
                        text = stringResource(R.string.no_agent),
                        color = Color.White.copy(0.55f),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Normal,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                } else {
                    Spacer(Modifier.height(10.dp))

                    // Detect when user scrolls to bottom
                    LaunchedEffect(listState) {
                        snapshotFlow { listState.layoutInfo.visibleItemsInfo }
                            .collect { visibleItems ->
                                val lastVisibleItem = visibleItems.lastOrNull()
                                val totalItems = listState.layoutInfo.totalItemsCount

                                if (
                                    lastVisibleItem != null &&
                                    lastVisibleItem.index >=
                                    totalItems - 3 && // Trigger 3 items before end
                                    !isLoading &&
                                    agents.isNotEmpty()
                                ) {
                                    onLoadMore()
                                }
                            }
                    }

                    LazyVerticalGrid(
                        state = listState,
                        modifier = Modifier.padding(horizontal = 16.dp),
                        columns = GridCells.Fixed(2),
                        contentPadding = PaddingValues(bottom = innerPadding.calculateBottomPadding() + 100.dp),
                        horizontalArrangement = Arrangement.spacedBy(13.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp),
                    ) {
                        runCatching {
                            if (agents.isNotEmpty()) {
                                itemsIndexed(
                                    items = agents,
                                    key = { index, agent -> "${agent.id}_$index" },
                                ) { index, agent ->
                                    MyAgentCard(
                                        modifier =
                                            Modifier.noRippleClickable { onClickAgent(agent) },
                                        agentInfo = agent,
                                        onEditAgent = onEditAgent,
                                        onDeleteAgent = onDeleteAgent,
                                    )
                                }
                            }
                        }.onFailure { it.printStackTrace() }

                        // Loading indicator when loading more (only show when there's no data)
                        if (isLoading && agents.isEmpty()) {
                            item(span = { GridItemSpan(maxLineSpan) }) {
                                Box(
                                    modifier = Modifier.padding(16.dp),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    CircularProgressIndicator(
                                        color = Color.White,
                                        modifier = Modifier.size(24.dp),
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

/** Profile Header 可折叠区域 */
@Composable
private fun ProfileHeader(
    modifier: Modifier,
    collapseProgress: Float, // 0f = 展开, 1f = 折叠
    userProfile: UserProfile,
    onShowSettings: () -> Unit,
    innerPadding: PaddingValues,
    context: android.content.Context,
) {
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    // Settings 图标位置固定，不响应折叠状态
    val topSpacerHeight = innerPadding.calculateTopPadding() + 28.dp

    Column(
        modifier = modifier.fillMaxWidth()
    ) {
        // 顶部间距和设置按钮 - 始终显示，位置固定
        Spacer(Modifier.height(topSpacerHeight))

        // 设置按钮行 - 始终显示
        Row {
            Spacer(Modifier.weight(1f))
            val context = LocalContext.current
            var lastClickTime by remember { mutableLongStateOf(0L) }

            AsyncImage(
                modifier = Modifier
                    .size(24.dp)
                    .clickable {
                        val currentTime = System.currentTimeMillis()
                        if (AntiClick.isValidClick(lastClickTime)) {
                            lastClickTime = currentTime
                            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                                onShowSettings()
                            } else {
                                context.startActivity(Intent(context, LoginActivity::class.java))
                            }
                        }
                    },
                model = R.drawable.icon_setting,
                contentDescription = null,
            )
            Spacer(Modifier.width(16.dp))
        }

        // 头像和昵称之间的间距根据折叠状态调整
        Spacer(Modifier.height(24.dp * (1f - collapseProgress * 0.5f)))

        // 头像和昵称 - 始终显示，但大小会变化
        Row(
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Spacer(Modifier.width(16.dp))

            // 头像大小根据折叠状态调整：展开时 120.dp，折叠时 60.dp
            val avatarSize = remember(collapseProgress) {
                120.dp * (1f - collapseProgress * 0.5f)
            }

            Box(
                modifier =
                    Modifier
                        .size(avatarSize)
                        .background(color = Color.White, shape = CircleShape)
                        .padding(4.dp)
            ) {
                AsyncImage(
                    modifier = Modifier
                        .fillMaxSize()
                        .clip(CircleShape),
                    model =
                        ImageRequest.Builder(context)
                            .data(getCdnImageUrl(userProfile.avatar, width = 512))
                            .build(),
                    placeholder = painterResource(R.drawable.app_icon),
                    error = painterResource(R.drawable.app_icon),
                    contentDescription = null,
                )
            }

            // 头像和昵称之间的间距根据折叠状态调整
            Spacer(Modifier.width(19.dp * (1f - collapseProgress * 0.3f)))

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = userProfile.nickname.ifEmpty { "Guest" },
                    color = Color.White,
                    fontSize = (20.sp.value * (1f - collapseProgress * 0.2f)).sp, // 折叠时稍微缩小
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    modifier = Modifier
                        .fillMaxWidth()
                        .noRippleClickable {
                            if (userProfile.id.isNotEmpty()) {
                                val clipboard = context.getSystemService<ClipboardManager>()
                                clipboard?.setPrimaryClip(
                                    ClipData.newPlainText(
                                        "User ID",
                                        userProfile.id,
                                    )
                                )
                                if (clipboard != null) {
                                    ToastUtils.showShort(R.string.toast_copied_to_clipboard)
                                }
                            }
                        },
                    text = stringResource(R.string.ID, userProfile.id),
                    color = Color.White.copy(0.55f),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Light,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            Spacer(Modifier.width(16.dp))
        }

        // Intro 和编辑按钮之间的间距 - 折叠时减少
        Spacer(Modifier.height(24.dp * (1f - collapseProgress)))

        // Intro 和编辑按钮 - 折叠时隐藏编辑按钮，但可以显示一行 intro
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .height(
                    if (collapseProgress >= 1f) 40.dp // 折叠时只显示一行 intro 的高度
                    else 60.dp * (1f - collapseProgress * 0.33f) // 展开时正常高度，折叠时逐渐减少
                ),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Intro 文本 - 折叠时只显示一行，展开时显示两行
            Text(
                modifier = Modifier
                    .weight(1f)
                    .alpha(if (collapseProgress >= 1f) 0.7f else 1f), // 折叠时稍微变透明
                text = userProfile.description ?: stringResource(R.string.persona_placeholder),
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                maxLines = if (collapseProgress >= 1f) 1 else 2, // 完全折叠时只显示一行
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(Modifier.width(8.dp))

            // 编辑按钮 - 折叠时隐藏
            Box(
                modifier = Modifier.alpha(1f - collapseProgress)
            ) {
                var lastClickTimeEdit by remember { mutableLongStateOf(0L) }

                AsyncImage(
                    modifier = Modifier
                        .size(40.dp)
                        .clickable {
                            val currentTime = System.currentTimeMillis()
                            if (AntiClick.isValidClick(lastClickTimeEdit)) {
                                lastClickTimeEdit = currentTime
                                if (IntySetting.isLogin() && IntySetting.getCurToken()
                                        .isNotEmpty()
                                ) {
                                    ModifyProfileActivity.launch(context, userProfile)
                                } else {
                                    context.startActivity(
                                        Intent(
                                            context,
                                            LoginActivity::class.java
                                        )
                                    )
                                }
                            }
                        },
                    model = R.drawable.icon_edit,
                    contentDescription = null,
                )
            }
        }

        // Intro 和 VIP Banner 之间的间距 - 折叠时减少
        Spacer(Modifier.height(24.dp * (1f - collapseProgress)))

        // VIP Banner - 折叠时隐藏
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .alpha(1f - collapseProgress)
                .height(
                    if (collapseProgress >= 1f) 0.dp
                    else 120.dp * (1f - collapseProgress)
                )
        ) {
            PremiumBanner(
                status = vipStatus.subscriptionStatus,
                purchaseTime = TimeUtils.formatTimestampToString(vipStatus.purchaseTime),
                expireTime = TimeUtils.formatTimestampToString(vipStatus.expiryTime),
                onClick = {
                    VipCenterActivity.launch(
                        context,
                        VipCenterActivity.PROFILE_UPGRADE
                    )
                },
            )
        }

        Spacer(Modifier.height(8.dp * (1f - collapseProgress)))
    }
}

@Composable
private fun MyAgentCard(
    modifier: Modifier,
    agentInfo: AgentInfo,
    onEditAgent: ((AgentInfo) -> Unit)? = null,
    onDeleteAgent: ((AgentInfo) -> Unit)? = null,
) {
    var showMenu by remember { mutableStateOf(false) }
    var showDeleteDialog by remember { mutableStateOf(false) }
    var lastClickTime by remember { mutableLongStateOf(0L) }

    // 判断是否有头像需要加载
    val hasAvatarToLoad = agentInfo.avatar.isNotEmpty()

    // 图片加载状态
    var imageLoaded by remember { mutableStateOf(false) }

    Box(
        modifier = modifier
            .size(165.dp, 220.dp)
            .clip(RoundedCornerShape(12.dp))
    ) {
        if (hasAvatarToLoad) {
            // 有头像需要加载时，使用 Shimmer 占位符
            if (!imageLoaded) {
                ShimmerPlaceholder(modifier = Modifier.fillMaxSize(), cornerRadius = 12.dp)
            }

            AsyncImage(
                modifier = Modifier.fillMaxSize(),
                model = ImageRequest.Builder(LocalContext.current).data(agentInfo.avatar).build(),
                contentDescription = null,
                placeholder = null, // 使用自定义的 Shimmer 占位显示
                error = null, // 加载失败时也使用 Shimmer 占位显示
                onSuccess = { imageLoaded = true },
                onError = { imageLoaded = false },
                contentScale = ContentScale.Crop,
                alignment = Alignment.TopCenter
            )
        } else {
            // 没有头像需要加载时，直接显示默认头像
            Image(
                modifier = Modifier.fillMaxSize(),
                painter = painterResource(R.drawable.img_default_avatar),
                contentDescription = null,
                contentScale = ContentScale.Crop,
            )
        }

        // 缓存渐变画笔，避免每次重组时重新创建
        val gradientBrush = remember {
            Brush.verticalGradient(
                colors = listOf(Color.Transparent, Color.Black.copy(.5f), Color.Black.copy(.9f))
            )
        }
        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .background(brush = gradientBrush)
                    .padding(8.dp)
                    .align(Alignment.BottomCenter),
            verticalArrangement = Arrangement.spacedBy(4.dp),
        ) {
            Text(
                modifier = Modifier,
                text = agentInfo.name,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
            Text(
                modifier = Modifier,
                text = agentInfo.intro,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                color = Color.White.copy(.7f),
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }

        // 右下角的菜单按钮
        if (onEditAgent != null || onDeleteAgent != null) {
            Box(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(4.dp)
            ) {
                Box(
                    modifier =
                        Modifier
                            .size(28.dp)
                            .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(4.dp))
                            .noRippleClickable(
                                onClick = {
                                    val currentTime = System.currentTimeMillis()
                                    if (AntiClick.isValidClick(lastClickTime)) {
                                        lastClickTime = currentTime
                                        showMenu = true
                                    }
                                }
                            ),
                    contentAlignment = Alignment.Center,
                ) {
                    AsyncImage(
                        modifier = Modifier.size(20.dp),
                        model = R.drawable.icon_more2,
                        contentDescription = null
                    )
                }

                DropdownMenu(expanded = showMenu, onDismissRequest = { showMenu = false }) {
                    onEditAgent?.let { editCallback ->
                        DropdownMenuItem(
                            text = {
                                Text(
                                    text = stringResource(R.string.edit_button),
                                    color = Color.White,
                                    fontSize = 14.sp,
                                )
                            },
                            onClick = {
                                showMenu = false
                                editCallback(agentInfo)
                            },
                        )
                    }

                    onDeleteAgent?.let { deleteCallback ->
                        DropdownMenuItem(
                            text = {
                                Text(
                                    text = stringResource(R.string.delete_button),
                                    color = Color.Red,
                                    fontSize = 14.sp,
                                )
                            },
                            onClick = {
                                showMenu = false
                                showDeleteDialog = true
                            },
                        )
                    }
                }
            }
        }

        // Delete confirmation dialog
        if (showDeleteDialog) {
            AlertDialog(
                onDismissRequest = { showDeleteDialog = false },
                title = {
                    Text(
                        text = stringResource(R.string.delete_character_full),
                        color = Color.White,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                },
                text = {
                    Text(
                        text =
                            stringResource(R.string.delete_character_confirm_full, agentInfo.name),
                        color = Color.White,
                        fontSize = 14.sp,
                    )
                },
                confirmButton = {
                    Button(
                        onClick = {
                            showDeleteDialog = false
                            onDeleteAgent?.invoke(agentInfo)
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color.Red),
                    ) {
                        Text(
                            text = stringResource(R.string.delete_button),
                            color = Color.White,
                            fontSize = 14.sp,
                        )
                    }
                },
                dismissButton = {
                    Button(
                        onClick = { showDeleteDialog = false },
                        colors = ButtonDefaults.buttonColors(containerColor = Color.Gray),
                    ) {
                        Text(
                            text = stringResource(R.string.cancel_button_full),
                            color = Color.White,
                            fontSize = 14.sp,
                        )
                    }
                },
                containerColor = Color(0xFF2A2A2A),
                titleContentColor = Color.White,
                textContentColor = Color.White,
            )
        }
    }
}

/** Premium Banner 组件 */
@Preview
@Composable
private fun PremiumBanner(
    status: String? = "Activate Now",
    purchaseTime: String? = null, // 购买日期
    expireTime: String? = null, // 过期时间
    onClick: () -> Unit = {},
) {
    val context = LocalContext.current
    var lastClickTimePremium by remember { mutableLongStateOf(0L) }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(120.dp)
            .padding(horizontal = 12.dp)
            .clickable {
                val currentTime = System.currentTimeMillis()
                if (AntiClick.isValidClick(lastClickTimePremium)) {
                    lastClickTimePremium = currentTime
                    if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                        onClick()
                    } else {
                        context.startActivity(Intent(context, LoginActivity::class.java))
                    }
                }
            }
    ) {
        Image(
            painter = painterResource(R.drawable.img_vip_banner),
            contentDescription = "",
            contentScale = ContentScale.FillWidth,
            modifier = Modifier.fillMaxWidth(),
        )

        Row(
            Modifier
                .border(
                    width = 0.5.dp,
                    color = Color(0x61D523FF),
                    shape = RoundedCornerShape(size = 12.dp),
                )
                .background(color = Color(0x33D216FF), shape = RoundedCornerShape(size = 12.dp))
                .padding(horizontal = 8.dp)
                .align(BiasAlignment(.95f, .1f)),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.Center,
        ) {
            // 三种UI状态显示，1. 无有效订阅 显示Activate Now；2. 有效订阅 显示Since 日期；3. 有订阅快过期 显示Expires ON 日期
            val str =
                when (status) {
                    VipStatus.UI_SUBSCRIBED -> "Since $purchaseTime"
                    VipStatus.UI_SUBSCRIBED_EXPIRE_SOON -> "Expires on $expireTime"
                    else -> "Activate now"
                }

            Text(
                text = str,
                fontSize = 16.sp,
                color = Color.White,
                textAlign = TextAlign.Center,
            )
        }
    }
}
