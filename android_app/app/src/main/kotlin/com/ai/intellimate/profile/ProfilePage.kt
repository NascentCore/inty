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
import ai.sxwl.android.design.theme.VibeModeColors
import ai.sxwl.android.utils.TimeUtils
import ai.sxwl.android.utils.ToastUtils
import android.app.Activity
import android.content.Context
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.HelpCenter
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
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
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.net.toUri
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.navigation.NavController
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.R
import com.ai.intellimate.agent.generate.CreateRoleDraft
import com.ai.intellimate.settings.check.CheckInActivity
import com.ai.intellimate.settings.playStoreUrl
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.UnlimitChatDialog
import com.ai.intellimate.ui.components.ShimmerPlaceholder
import com.ai.intellimate.vip.VipCenterActivity
import com.ai.intellimate.xb.navigation.Routes
import kotlin.math.abs
import kotlin.math.min
import kotlinx.coroutines.launch

/** "我的"页面 */
@Composable
internal fun ProfilePage(
    navController: NavController,
    modifier: Modifier,
    userProfile: UserProfile,
    agents: List<AgentInfo>,
    drafts: List<CreateRoleDraft> = emptyList(),
    onClickAgent: (AgentInfo) -> Unit,
    onClickDraft: ((String) -> Unit)? = null,
    onEditAgent: ((AgentInfo) -> Unit)? = null,
    onDeleteAgent: ((AgentInfo) -> Unit)? = null,
    isLoading: Boolean = false,
    onLoadMore: () -> Unit = {},
    onShowSettings: () -> Unit,
    vipStatus: VipStatus? = null, // 可选的 VIP 状态，用于预览
    profileViewModel: ProfileViewModel? = null, // 用于刷新用户信息
    appUpdateTips: Boolean = false, // 是否有更新提示
) {
    val context = LocalContext.current
    val density = LocalDensity.current
    val scope = rememberCoroutineScope()
    val validDrafts = drafts.filter { !it.isEmpty() }

    // 创建用于编辑个人资料的 launcher，在 ProfilePage 内部处理
    val editProfileLauncher =
        rememberLauncherForActivityResult(
            contract = ActivityResultContracts.StartActivityForResult()
        ) { result ->
            // 从 ModifyProfileActivity 返回后，刷新用户信息
            if (result.resultCode == Activity.RESULT_OK) {
                profileViewModel?.updateUserInfoLocal()
            }
        }

    // 使用 PageTrackingHelper 进行页面跟踪
    LaunchedEffect(Unit) {
        PageTrackingHelper.trackPageView(
            "ProfilePage",
            "MainActivity",
            mapOf("agent_count" to agents.size, "is_loading" to isLoading),
        )
    }

    // 监听页面恢复，自动刷新用户信息（从 ModifyProfileActivity 返回时会触发）
    if (profileViewModel != null) {
        LifecycleResumeEffect(profileViewModel) {
            profileViewModel.updateUserInfoLocal()
            onPauseOrDispose {}
        }
    }

    // 折叠相关状态
    val maxCollapseOffset =
        with(density) {
            (UiConfigs.MePage.HeaderMaxHeight - UiConfigs.MePage.HeaderMinHeight).toPx()
        } // 最大折叠距离

    val collapseOffset = remember { Animatable(0f) }

    // 计算折叠比例 (0f = 完全展开, 1f = 完全折叠)
    val collapseProgress by remember {
        derivedStateOf { (collapseOffset.value / maxCollapseOffset).coerceIn(0f, 1f) }
    }

    // LazyGrid state - 需要在 nestedScrollConnection 之前创建
    val listState = rememberLazyGridState()

    // 监听用户ID变化，当切换账号时重置滚动状态和折叠状态
    var previousUserId by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(userProfile.id) {
        val currentUserId = userProfile.id
        // 当用户ID变化且不是首次加载时，重置滚动位置和折叠状态
        if (
            currentUserId.isNotEmpty() && previousUserId != null && previousUserId != currentUserId
        ) {
            // 用户ID发生变化，重置滚动位置和折叠状态
            listState.animateScrollToItem(0)
            collapseOffset.snapTo(0f)
        }
        // 更新上一次的用户ID
        if (currentUserId.isNotEmpty()) {
            previousUserId = currentUserId
        }
    }

    // 嵌套滚动连接 - 处理折叠逻辑
    val nestedScrollConnection =
        remember(listState) {
            object : NestedScrollConnection {
                override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                    // 向上滚动 (available.y < 0) - 优先折叠 header
                    if (available.y < 0 && collapseOffset.value < maxCollapseOffset) {
                        val remainingToCollapse = maxCollapseOffset - collapseOffset.value
                        val toConsume = min(abs(available.y), remainingToCollapse)
                        scope.launch { collapseOffset.snapTo(collapseOffset.value + toConsume) }
                        // 返回消费的滚动量（负数表示向上滚动）
                        return Offset(0f, -toConsume)
                    }

                    // 向下滚动 (available.y > 0) - 优先展开 header
                    if (available.y > 0 && collapseOffset.value > 0f) {
                        // 检查 LazyGrid 是否已经滚动到顶部
                        // 只有当 LazyGrid 在顶部时，才展开 header
                        if (
                            listState.firstVisibleItemIndex == 0 &&
                                listState.firstVisibleItemScrollOffset == 0
                        ) {
                            val toConsume = min(available.y, collapseOffset.value)
                            scope.launch { collapseOffset.snapTo(collapseOffset.value - toConsume) }
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
                            collapseOffset.animateTo(maxCollapseOffset, animationSpec = tween(300))
                        }
                        // 消费部分速度，剩余速度传递给 LazyGrid
                        val remainingVelocity =
                            Velocity(0f, currentVelocity * (1f - collapseProgress))
                        return remainingVelocity
                    }

                    // 向下滑动 - 继续展开到完全展开状态
                    if (currentVelocity > 0 && collapseOffset.value > 0f) {
                        // 只有当 LazyGrid 在顶部时才展开
                        if (
                            listState.firstVisibleItemIndex == 0 &&
                                listState.firstVisibleItemScrollOffset == 0
                        ) {
                            scope.launch {
                                collapseOffset.animateTo(0f, animationSpec = tween(300))
                            }
                            // 消费部分速度
                            val remainingVelocity = Velocity(0f, currentVelocity * collapseProgress)
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
            contentDescription = null,
        )
        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent,
        ) { innerPadding ->
            Column(modifier = Modifier.fillMaxWidth().nestedScroll(nestedScrollConnection)) {
                // Header 区域 - 可折叠
                ProfileHeader(
                    navController,
                    modifier = Modifier,
                    collapseProgress = collapseProgress,
                    userProfile = userProfile,
                    onShowSettings = onShowSettings,
                    innerPadding = innerPadding,
                    context = context,
                    vipStatus = vipStatus,
                    editProfileLauncher = editProfileLauncher,
                    appUpdateTips = appUpdateTips,
                )

                // LazyGrid 区域
                if (validDrafts.isEmpty() && agents.isEmpty()) {
                    Spacer(Modifier.height(UiConfigs.MePage.EmptyStateTopSpacing))

                    AsyncImage(
                        modifier = Modifier.align(Alignment.CenterHorizontally),
                        model = R.drawable.img_content_empty,
                        contentDescription = null,
                    )

                    Spacer(Modifier.height(UiConfigs.MePage.EmptyStateBottomSpacing))

                    Text(
                        modifier =
                            Modifier.padding(horizontal = UiConfigs.Padding.ScreenHorizontal)
                                .align(Alignment.CenterHorizontally),
                        text = stringResource(R.string.no_agent),
                        color = Color.White.copy(0.55f),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Normal,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                } else {
                    Spacer(Modifier.height(UiConfigs.MePage.EmptyStateContentSpacing))

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
                        modifier =
                            Modifier.padding(horizontal = UiConfigs.MePage.GridHorizontalPadding),
                        columns = GridCells.Fixed(2),
                        contentPadding =
                            PaddingValues(
                                bottom =
                                    innerPadding.calculateBottomPadding() +
                                        UiConfigs.MePage.GridContentBottomPadding
                            ),
                        horizontalArrangement =
                            Arrangement.spacedBy(UiConfigs.MePage.GridHorizontalSpacing),
                        verticalArrangement =
                            Arrangement.spacedBy(UiConfigs.MePage.GridVerticalSpacing),
                    ) {
                        // 显示所有草稿卡片
                        if (validDrafts.isNotEmpty() && onClickDraft != null) {
                            validDrafts.forEach { draft ->
                                item(key = "draft_${draft.id}") {
                                    DraftAgentCard(
                                        modifier =
                                            Modifier.noRippleClickable { onClickDraft(draft.id) },
                                        draft = draft,
                                    )
                                }
                            }
                        }

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
                            }
                            .onFailure { it.printStackTrace() }

                        // Loading indicator when loading more (only show when there's no data)
                        if (isLoading && agents.isEmpty()) {
                            item(span = { GridItemSpan(maxLineSpan) }) {
                                Box(
                                    modifier = Modifier.padding(UiConfigs.Padding.ScreenHorizontal),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    CircularProgressIndicator(
                                        color = Color.White,
                                        modifier = Modifier.size(UiConfigs.MePage.TopIconsRow.Size),
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
    navController: NavController,
    modifier: Modifier,
    collapseProgress: Float, // 0f = 展开, 1f = 折叠
    userProfile: UserProfile,
    onShowSettings: () -> Unit,
    innerPadding: PaddingValues,
    context: Context,
    vipStatus: VipStatus? = null, // 可选的 VIP 状态，用于预览
    editProfileLauncher: ActivityResultLauncher<Intent>, // 编辑个人资料的 launcher
    appUpdateTips: Boolean = false, // 是否有更新提示
) {
    // 如果提供了 vipStatus 参数，使用它；否则从 BillingRepository 获取并响应Flow变化
    // 使用 collectAsState() 来响应 Flow 的变化，确保订阅状态更新时UI能及时刷新
    // 当 BillingRepository.vipStatusFlow 的值变化时，Compose 会自动重新组合此组件
    val vipStatusFromFlow by BillingRepository.vipStatusFlow.collectAsState()
    // 预览模式下使用传入的 vipStatus，正常模式下使用 Flow 的值
    // 当 vipStatusFromFlow 变化时，currentVipStatus 会自动重新计算
    val currentVipStatus = vipStatus ?: vipStatusFromFlow
    val isSubscribed = currentVipStatus.isSubscribed
    var showSubscribeDialog by remember { mutableStateOf(false) }

    if (showSubscribeDialog) {
        val dialogData =
            ChatDialogData(
                R.drawable.img_unlimit_dialog_bg,
                stringResource(R.string.str_unlimit_dialog_content),
                stringResource(R.string.str_unlimit_btn_text),
            )

        UnlimitChatDialog(
            dialogData = dialogData,
            onCancel = { showSubscribeDialog = false },
            onSure = {
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                    VipCenterActivity.launch(context, VipCenterActivity.PROFILE_UPGRADE)
                }
                showSubscribeDialog = false
            },
            onMoreInfo = {
                if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                    VipCenterActivity.launch(context, VipCenterActivity.PROFILE_UPGRADE)
                }
                showSubscribeDialog = false
            },
        )
    }

    // Settings 图标位置固定，不响应折叠状态
    val topSpacerHeight = innerPadding.calculateTopPadding() + UiConfigs.MePage.TopSpacerOffset

    Column(modifier = modifier.fillMaxWidth()) {
        // 顶部间距和设置按钮 - 始终显示，位置固定
        Spacer(Modifier.height(topSpacerHeight))

        // 设置按钮行 - 始终显示
        Row(verticalAlignment = Alignment.CenterVertically) {
            Spacer(Modifier.weight(1f))
            var lastClickTime by remember { mutableLongStateOf(0L) }

            Icon(
                modifier =
                    Modifier.size(UiConfigs.MePage.TopIconsRow.Size).clickable {
                        val currentTime = System.currentTimeMillis()
                        if (AntiClick.isValidClick(lastClickTime)) {
                            lastClickTime = currentTime
                            try {
                                val intent =
                                    Intent(Intent.ACTION_VIEW, UiConfigs.Urls.HelpCenter.toUri())
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                context.startActivity(intent)
                            } catch (e: Exception) {
                                ToastUtils.showLargeText(e.toString())
                            }
                        }
                    },
                imageVector = Icons.AutoMirrored.Rounded.HelpCenter,
                contentDescription = stringResource(R.string.me_icons_row_help),
                tint = Color.White,
            )

            Spacer(Modifier.width(UiConfigs.MePage.TopIconsRow.Spacing))

            AsyncImage(
                modifier =
                    Modifier.size(UiConfigs.MePage.TopIconsRow.Size).clickable {
                        val currentTime = System.currentTimeMillis()
                        if (AntiClick.isValidClick(lastClickTime)) {
                            lastClickTime = currentTime
                            try {
                                val intent =
                                    Intent(Intent.ACTION_VIEW, UiConfigs.Urls.DiscordInvite.toUri())
                                // 确保新的 Activity 不在当前任务栈中启动，这通常是一个良好的实践
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                context.startActivity(intent)
                            } catch (e: Exception) {
                                ToastUtils.showLargeText(e.toString())
                            }
                        }
                    },
                model = R.drawable.ic_discord,
                contentDescription = stringResource(R.string.me_icons_row_discord),
            )

            Spacer(Modifier.width(UiConfigs.MePage.TopIconsRow.Spacing))

            AsyncImage(
                modifier =
                    Modifier.size(UiConfigs.MePage.TopIconsRow.Size).clickable {
                        val currentTime = System.currentTimeMillis()
                        if (AntiClick.isValidClick(lastClickTime)) {
                            lastClickTime = currentTime
                            try {
                                val intent =
                                    Intent(
                                        Intent.ACTION_VIEW,
                                        UiConfigs.Urls.WhatsAppGroupInvite.toUri(),
                                    )
                                // 确保新的 Activity 不在当前任务栈中启动，这通常是一个良好的实践
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                                context.startActivity(intent)
                            } catch (e: Exception) {
                                ToastUtils.showLargeText(e.toString())
                            }
                        }
                    },
                model = R.drawable.ic_whatsapp,
                contentDescription = stringResource(R.string.me_icons_row_whatsapp),
            )
            Spacer(Modifier.width(UiConfigs.MePage.TopIconsRow.Spacing))

            AsyncImage(
                modifier =
                    Modifier.size(24.dp).clickable {
                        val currentTime = System.currentTimeMillis()
                        if (AntiClick.isValidClick(lastClickTime)) {
                            lastClickTime = currentTime
                            //                                            try {
                            //
                            // ToastUtils.showShort("Not Implementation！")
                            //                                            } catch (e: Exception) {
                            //
                            // ToastUtils.showLargeText(e.toString())
                            //                                            }
                            CheckInActivity.launch(context)
                        }
                    },
                model = R.drawable.ic_checkin,
                contentDescription = null,
            )
            Spacer(Modifier.width(8.dp))

            AsyncImage(
                modifier =
                    Modifier.size(UiConfigs.MePage.TopIconsRow.Size).clickable {
                        val currentTime = System.currentTimeMillis()
                        if (AntiClick.isValidClick(lastClickTime)) {
                            lastClickTime = currentTime
                            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                                navController.navigate(Routes.Settings)
                            }
                        }
                    },
                model = R.drawable.icon_setting,
                contentDescription = stringResource(R.string.me_icons_row_settings),
            )
            Spacer(Modifier.width(UiConfigs.MePage.TopIconsRow.RightPadding))
        }

        // 头像和昵称之间的间距根据折叠状态调整
        Spacer(Modifier.height(UiConfigs.MePage.SectionSpacing * (1f - collapseProgress * 0.5f)))

        // 头像和昵称 - 始终显示，但大小会变化
        Row(verticalAlignment = Alignment.CenterVertically) {
            Spacer(Modifier.width(UiConfigs.Padding.ScreenHorizontal))

            // 头像大小根据折叠状态调整：展开时 120.dp，折叠时 60.dp
            val avatarSize =
                remember(collapseProgress) {
                    UiConfigs.MePage.AvatarFullSize * (1f - collapseProgress * 0.5f)
                }

            // 头像点击防抖
            var lastClickTimeAvatar by remember { mutableLongStateOf(0L) }

            Box(
                modifier =
                    Modifier.size(avatarSize)
                        .background(color = Color.White, shape = CircleShape)
                        .padding(UiConfigs.MePage.AvatarPadding)
                // fixme clickable 为临时测试代码，需要删除
                //                        .clickable{
                //                            if (AppUtils.isAppDebug()){
                //                                val currentTime = System.currentTimeMillis()
                //                                if (AntiClick.isValidClick(lastClickTimeAvatar)) {
                //                                    lastClickTimeAvatar = currentTime
                //                                    // 使用预加载的推荐agents数据（explore agents），取前 12
                // 个用于展示
                //                                    val recommendedAgents =
                // UnifiedStartupManager.getCurrentRecommendedAgents()
                //                                    val agentsToShow = recommendedAgents.take(12)
                //                                    if (agentsToShow.isNotEmpty()) {
                //                                        SpecialDetailActivity.launch(
                //                                            context = context,
                //                                            themeId = "profile_preview_theme",
                //                                            themeTitle = "# Merry Christmas",
                //                                            themeDescription = "Ready for some
                // holiday magic? Meet our brand-new Christmas-themed AI companion—sparkly,
                // cheerful, and here to light up your winter feed. Come take a look and get into
                // the festive spirit!Ready for some holiday EndOfText.",
                //                                            isChristmas = true,
                //                                            agents = agentsToShow,
                //                                        )
                //                                    }
                //                                }
                //                            }
                //                        }
            ) {
                // 使用头像 URL 作为 key，确保头像更新时重新加载
                val avatarUrl = getCdnImageUrl(userProfile.avatar, width = 512)
                key(avatarUrl) { // 使用 key 确保 URL 变化时重新创建组件
                    AsyncImage(
                        modifier = Modifier.fillMaxSize().clip(CircleShape),
                        model = ImageRequest.Builder(context).data(avatarUrl).build(),
                        placeholder = painterResource(R.drawable.app_icon),
                        error = painterResource(R.drawable.app_icon),
                        contentDescription = null,
                    )
                }
            }

            // 头像和昵称之间的间距根据折叠状态调整
            Spacer(
                Modifier.width(
                    UiConfigs.MePage.AvatarToNicknameSpacing * (1f - collapseProgress * 0.3f)
                )
            )

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = userProfile.nickname.ifEmpty { "Guest" },
                    color = Color.White,
                    fontSize = (20.sp.value * (1f - collapseProgress * 0.2f)).sp, // 折叠时稍微缩小
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }

            Spacer(Modifier.width(UiConfigs.Padding.ScreenHorizontal))
        }

        // Intro 和编辑按钮之间的间距 - 折叠时减少
        Spacer(Modifier.height(UiConfigs.MePage.SectionSpacing * (1f - collapseProgress)))

        // Intro 和编辑按钮 - 折叠时隐藏编辑按钮，但可以显示一行 intro
        Row(
            modifier =
                Modifier.fillMaxWidth()
                    .padding(horizontal = UiConfigs.Padding.ScreenHorizontal)
                    .height(
                        if (collapseProgress >= 1f)
                            UiConfigs.MePage.IntroSectionCollapsedHeight // 折叠时只显示一行 intro 的高度
                        else
                            UiConfigs.MePage.IntroSectionExpandedHeight *
                                (1f - collapseProgress * 0.33f) // 展开时正常高度，折叠时逐渐减少
                    ),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // Intro 文本 - 折叠时只显示一行，展开时显示两行
            Text(
                modifier =
                    Modifier.weight(1f).alpha(if (collapseProgress >= 1f) 0.7f else 1f), // 折叠时稍微变透明
                text = userProfile.description ?: stringResource(R.string.persona_placeholder),
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                maxLines = if (collapseProgress >= 1f) 1 else 2, // 完全折叠时只显示一行
                overflow = TextOverflow.Ellipsis,
            )

            Spacer(Modifier.width(UiConfigs.MePage.TopIconsRow.Spacing))

            // 编辑按钮 - 折叠时隐藏
            Box(modifier = Modifier.alpha(1f - collapseProgress)) {
                var lastClickTimeEdit by remember { mutableLongStateOf(0L) }

                AsyncImage(
                    modifier =
                        Modifier.size(UiConfigs.MePage.EditButtonSize).clickable {
                            val currentTime = System.currentTimeMillis()
                            if (AntiClick.isValidClick(lastClickTimeEdit)) {
                                lastClickTimeEdit = currentTime
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
                                    // 使用 launcher 启动 ModifyProfileActivity，返回后会自动刷新用户信息
                                    val intent =
                                        Intent(context, ModifyProfileActivity::class.java).apply {
                                            putExtra("intent_key_agent_info", userProfile)
                                        }
                                    editProfileLauncher.launch(intent)
                                }
                            }
                        },
                    model = R.drawable.icon_edit,
                    contentDescription = null,
                )
            }
        }

        // Intro 和 VIP Banner 之间的间距 - 折叠时减少
        Spacer(Modifier.height(UiConfigs.MePage.SectionSpacing * (1f - collapseProgress)))

        // VIP Banner - 折叠时隐藏，宽度适配屏幕（不含padding），高度 120.dp
        if (collapseProgress < 1f) {
            Box(
                modifier =
                    Modifier.fillMaxWidth()
                        .alpha(1f - collapseProgress)
                        .height(UiConfigs.MePage.VipBannerHeight * (1f - collapseProgress)),
                contentAlignment = Alignment.Center,
            ) {
                PremiumBanner(
                    status = currentVipStatus.subscriptionStatus,
                    purchaseTime = TimeUtils.formatTimestampToString(currentVipStatus.purchaseTime),
                    expireTime = TimeUtils.formatTimestampToString(currentVipStatus.expiryTime),
                    onClick = {
                        VipCenterActivity.launch(context, VipCenterActivity.PROFILE_UPGRADE)
                    },
                )
            }

            if (BuildConfig.DEBUG) {
                Spacer(Modifier.height(UiConfigs.MePage.SectionSpacing * (1f - collapseProgress)))

                VibeModeBanner(
                    modifier =
                        Modifier.alpha(1f - collapseProgress)
                            .padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
                    isSubscribed = isSubscribed,
                    onRequestSubscribe = { showSubscribeDialog = true },
                )
            }

            if (appUpdateTips) {
                Spacer(Modifier.height(UiConfigs.MePage.SectionSpacing * (1f - collapseProgress)))
                NewVersionBanner(
                    modifier =
                        Modifier.fillMaxWidth()
                            .padding(horizontal = UiConfigs.Padding.ScreenHorizontal)
                )
            }
        }

        Spacer(Modifier.height(UiConfigs.MePage.BottomSpacing * (1f - collapseProgress)))
    }
}

@Composable
private fun DraftAgentCard(modifier: Modifier, draft: CreateRoleDraft) {
    val previewImage = remember(draft) { draft.primaryImageUrl() }
    val gradientBrush = remember {
        Brush.verticalGradient(
            colors = listOf(Color.Transparent, Color.Black.copy(.5f), Color.Black.copy(.9f))
        )
    }
    val badgeShape = RoundedCornerShape(percent = 50)
    val badgeVerticalPadding = UiConfigs.Spacing.Tiny / 2
    val displayName = draft.name.ifBlank { stringResource(R.string.draft_card_placeholder_name) }
    val subtitle =
        when {
            draft.intro.isNotBlank() -> draft.intro
            draft.opening.isNotBlank() -> draft.opening
            draft.settings.isNotBlank() -> draft.settings
            else -> stringResource(R.string.draft_card_placeholder_intro)
        }

    Box(
        modifier =
            modifier
                .size(UiConfigs.MePage.AgentCardWidth, UiConfigs.MePage.AgentCardHeight)
                .clip(RoundedCornerShape(UiConfigs.MePage.AgentCardCornerRadius))
    ) {
        if (!previewImage.isNullOrBlank()) {
            AsyncImage(
                modifier = Modifier.fillMaxSize(),
                model = ImageRequest.Builder(LocalContext.current).data(previewImage).build(),
                contentDescription = null,
                contentScale = ContentScale.Crop,
                alignment = Alignment.TopCenter,
            )
        } else {
            Image(
                modifier = Modifier.fillMaxSize(),
                painter = painterResource(R.drawable.img_default_avatar),
                contentDescription = null,
                contentScale = ContentScale.Crop,
            )
        }

        Box(
            modifier =
                Modifier.align(Alignment.TopStart)
                    .padding(UiConfigs.MePage.AgentCardPadding)
                    .background(Color.Black.copy(alpha = 0.65f), badgeShape)
                    .padding(horizontal = UiConfigs.Spacing.Small, vertical = badgeVerticalPadding)
        ) {
            Text(
                text = stringResource(R.string.draft_badge_label),
                color = Color.White,
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium,
            )
        }

        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .background(brush = gradientBrush)
                    .padding(UiConfigs.MePage.AgentCardPadding)
                    .align(Alignment.BottomCenter),
            verticalArrangement = Arrangement.spacedBy(UiConfigs.MePage.AgentCardTextSpacing),
        ) {
            Text(
                text = displayName,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
            Text(
                text = subtitle,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                color = Color.White.copy(.7f),
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
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
        modifier =
            modifier
                .size(UiConfigs.MePage.AgentCardWidth, UiConfigs.MePage.AgentCardHeight)
                .clip(RoundedCornerShape(UiConfigs.MePage.AgentCardCornerRadius))
    ) {
        if (hasAvatarToLoad) {
            // 有头像需要加载时，使用 Shimmer 占位符
            if (!imageLoaded) {
                ShimmerPlaceholder(
                    modifier = Modifier.fillMaxSize(),
                    cornerRadius = UiConfigs.MePage.AgentCardCornerRadius,
                )
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
                alignment = Alignment.TopCenter,
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
                Modifier.fillMaxWidth()
                    .background(brush = gradientBrush)
                    .padding(UiConfigs.MePage.AgentCardPadding)
                    .align(Alignment.BottomCenter),
            verticalArrangement = Arrangement.spacedBy(UiConfigs.MePage.AgentCardTextSpacing),
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
                modifier =
                    Modifier.align(Alignment.BottomEnd).padding(UiConfigs.MePage.AvatarPadding)
            ) {
                Box(
                    modifier =
                        Modifier.size(UiConfigs.MePage.AgentCardMenuButtonSize)
                            .background(
                                Color.Black.copy(alpha = 0.5f),
                                RoundedCornerShape(UiConfigs.MePage.AgentCardMenuButtonCornerRadius),
                            )
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
                        modifier = Modifier.size(UiConfigs.MePage.AgentCardMenuIconSize),
                        model = R.drawable.icon_more2,
                        contentDescription = null,
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

private fun CreateRoleDraft.primaryImageUrl(): String? {
    if (!croppedAvatarUrl.isNullOrBlank()) return croppedAvatarUrl
    val galleryUrl = avatarUrls.firstOrNull { it.isNotBlank() }
    if (!galleryUrl.isNullOrBlank()) return galleryUrl
    return avatarUrl?.takeIf { it.isNotBlank() }
}

/** Premium Banner 组件 */
@Composable
private fun PremiumBanner(
    status: String? = "Activate Now",
    purchaseTime: String? = null, // 购买日期
    expireTime: String? = null, // 过期时间
    onClick: () -> Unit = {},
) {
    var lastClickTimePremium by remember { mutableLongStateOf(0L) }

    // 使用 fillMaxWidth 适配屏幕宽度（不含padding），高度保持 120.dp
    Box(
        modifier =
            Modifier.fillMaxWidth().height(UiConfigs.MePage.VipBannerHeight).clickable {
                val currentTime = System.currentTimeMillis()
                if (AntiClick.isValidClick(lastClickTimePremium)) {
                    lastClickTimePremium = currentTime
                    if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                        onClick()
                    }
                }
            }
    ) {
        // 使用 FillBounds 填充整个区域，适配屏幕宽度
        Image(
            painter = painterResource(R.drawable.img_vip_banner),
            contentDescription = "",
            contentScale = ContentScale.FillBounds,
            modifier = Modifier.fillMaxSize(),
        )

        Row(
            Modifier.border(
                    width = 0.5.dp,
                    color = Color(0x61D523FF),
                    shape = RoundedCornerShape(size = UiConfigs.MePage.AgentCardCornerRadius),
                )
                .background(
                    color = Color(0x33D216FF),
                    shape = RoundedCornerShape(size = UiConfigs.MePage.AgentCardCornerRadius),
                )
                .padding(horizontal = UiConfigs.MePage.TopIconsRow.Spacing)
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

            Text(text = str, fontSize = 16.sp, color = Color.White, textAlign = TextAlign.Center)
        }
    }
}

// TODO: 当前是一个 on/off 滑动开关，改为点了之后直接打开/关闭的整体条幅。
@Composable
private fun VibeModeBanner(
    modifier: Modifier = Modifier,
    isSubscribed: Boolean,
    onRequestSubscribe: () -> Unit,
) {
    var vibeEnabled by rememberSaveable(isSubscribed) { mutableStateOf(false) }
    val isActive = isSubscribed && vibeEnabled

    val backgroundBrush =
        when {
            !isSubscribed ->
                Brush.linearGradient(
                    listOf(VibeModeColors.DisabledStart, VibeModeColors.DisabledEnd)
                )

            isActive ->
                Brush.horizontalGradient(
                    listOf(VibeModeColors.ActiveStart, VibeModeColors.ActiveEnd)
                )

            else ->
                Brush.horizontalGradient(
                    listOf(VibeModeColors.InactiveStart, VibeModeColors.InactiveEnd)
                )
        }

    val shape = RoundedCornerShape(UiConfigs.MePage.VibeMode.CornerRadius)
    val borderColor =
        if (isActive) Color.White.copy(alpha = 0.45f)
        else Color.White.copy(alpha = UiConfigs.Alpha.SubtleBorder)

    val switchColors =
        SwitchDefaults.colors(
            checkedThumbColor = Color.White,
            checkedTrackColor = VibeModeColors.SwitchTrackActive,
            uncheckedThumbColor = Color.White,
            uncheckedTrackColor =
                if (isSubscribed) VibeModeColors.SwitchTrackInactive
                else VibeModeColors.SwitchTrackDisabled,
            checkedBorderColor = Color.Transparent,
            uncheckedBorderColor = Color.Transparent,
            disabledCheckedThumbColor = Color.White,
            disabledCheckedTrackColor = VibeModeColors.SwitchTrackActive,
            disabledUncheckedThumbColor = Color.White.copy(alpha = UiConfigs.Alpha.DisabledButton),
            disabledUncheckedTrackColor = VibeModeColors.SwitchTrackDisabled,
            disabledCheckedBorderColor = Color.Transparent,
            disabledUncheckedBorderColor = Color.Transparent,
        )

    val baseModifier =
        modifier
            .clip(shape)
            .background(brush = backgroundBrush, shape = shape)
            .border(
                width = UiConfigs.MePage.VibeMode.BorderWidth,
                color = borderColor,
                shape = shape,
            )
            .padding(UiConfigs.MePage.VibeMode.InnerPadding)

    Row(
        modifier =
            baseModifier.then(
                if (isSubscribed) {
                    Modifier
                } else {
                    Modifier.clickable(onClick = onRequestSubscribe)
                }
            ),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text =
                    stringResource(
                        if (isActive) R.string.vibe_mode_active_title else R.string.vibe_mode_title
                    ),
                color = Color.White,
                fontSize = UiConfigs.Typography.ButtonLarge,
                fontWeight = FontWeight.SemiBold,
            )

            if (!isActive) {
                Spacer(Modifier.height(UiConfigs.Spacing.Small))
                Text(
                    text = stringResource(R.string.vibe_mode_subtitle),
                    color = Color.White.copy(alpha = UiConfigs.Alpha.DimmedText),
                    fontSize = UiConfigs.Typography.Support,
                    lineHeight = UiConfigs.LineHeight.Support,
                )
            }
        }

        Spacer(Modifier.width(UiConfigs.MePage.VibeMode.ContentSpacing))

        val switchWrapperModifier =
            if (isSubscribed) {
                Modifier
            } else {
                Modifier.clickable(onClick = onRequestSubscribe)
            }

        val toggleContentDescription = stringResource(R.string.vibe_mode_toggle_content_desc)

        Box(modifier = switchWrapperModifier) {
            Switch(
                checked = isActive,
                onCheckedChange = { checked -> vibeEnabled = checked },
                enabled = isSubscribed,
                colors = switchColors,
                modifier = Modifier.semantics { contentDescription = toggleContentDescription },
            )
        }
    }
}

/** ProfilePage 预览 */
@Preview(showBackground = true, backgroundColor = 0xFF000000)
@Composable
private fun ProfilePagePreview() {
    // 创建预览用的 VIP 状态
    val previewVipStatus =
        VipStatus(
            isSubscribed = false,
            subscriptionStatus = VipStatus.UI_UNSUBSCRIBED,
            purchaseTime = null,
            expiryTime = null,
        )

    // 创建预览用的用户数据
    val previewUserProfile =
        UserProfile(
            id = "preview_user_123",
            nickname = "Preview User",
            avatar = "",
            description =
                "This is a preview user profile description. It can be quite long to test the text truncation and layout.",
            email = "preview@example.com",
            gender = "MALE",
            ageGroup = "25-30",
            systemLanguage = "en",
            isActive = true,
            isSuperuser = false,
            publicAgentsCount = 5,
            totalAgentsFollows = 10,
            followerCount = 20,
            connectorCount = 15,
        )

    // 创建预览用的 Agent 列表
    val previewAgents =
        listOf(
            AgentInfo(
                id = "agent_1",
                name = "Agent One",
                intro = "This is the first agent with a longer description to test text overflow.",
                avatar = "",
                background = "",
                category = "Fantasy",
                gender = "FEMALE",
                tags = listOf("romance", "fantasy", "adventure"),
            ),
            AgentInfo(
                id = "agent_2",
                name = "Agent Two",
                intro = "Second agent description.",
                avatar = "",
                background = "",
                category = "Sci-Fi",
                gender = "MALE",
                tags = listOf("sci-fi", "action"),
            ),
            AgentInfo(
                id = "agent_3",
                name = "Agent Three",
                intro =
                    "Third agent with a very long description that should be truncated properly in the card layout.",
                avatar = "",
                background = "",
                category = "Romance",
                gender = "FEMALE",
                tags = listOf("romance", "drama"),
            ),
            AgentInfo(
                id = "agent_4",
                name = "Agent Four",
                intro = "Fourth agent.",
                avatar = "",
                background = "",
                category = "Mystery",
                gender = "MALE",
                tags = listOf("mystery", "thriller"),
            ),
        )
}

/** 新版本提示 Banner */
@Composable
private fun NewVersionBanner(modifier: Modifier = Modifier) {
    val uriHandler = LocalUriHandler.current

    // 高亮时使用醒目的渐变（从紫色到橙色），普通时使用半透明白色
    val backgroundBrush =
        Brush.horizontalGradient(
            colors =
                listOf(
                    Color(0xFFC122FF), // 紫色
                    Color(0xFFFF905D), // 橙色
                )
        )

    val textColor = Color.White

    Box(
        modifier =
            modifier
                .height(56.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(backgroundBrush)
                .clickable { uriHandler.openUri(playStoreUrl()) },
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = stringResource(R.string.str_suggest_upgrade),
            color = textColor,
            fontSize = 16.sp,
            fontWeight = FontWeight.Medium,
        )
    }
}
