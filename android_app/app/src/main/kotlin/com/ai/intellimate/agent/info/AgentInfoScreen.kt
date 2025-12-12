package com.ai.intellimate.agent.info

import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.utils.ToastUtils
import androidx.annotation.StringRes
import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ArrowDropDown
import androidx.compose.material.icons.rounded.ArrowDropUp
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.navigation.compose.rememberNavController
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostConfig
import com.ai.intellimate.boost.BoostError
import com.ai.intellimate.boost.BoostException
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.boost.ui.BoostSheet
import com.ai.intellimate.boost.ui.BoostStatusChip
import com.ai.intellimate.chat.ui.FullScreenImageViewer
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.AgentBackground
import com.ai.intellimate.ui.components.SmartTagsLayout
import com.ai.intellimate.utils.formatDisplayId
import java.util.Locale
import kotlinx.coroutines.launch

private const val CLIPBOARD_LABEL_AGENT_ID = "Agent ID"

private enum class AgentGenderPronoun(@StringRes val labelRes: Int) {
    Female(R.string.she_her),
    Male(R.string.he_him),
    Other(R.string.they_them);

    companion object {
        fun from(rawGender: String): AgentGenderPronoun? {
            if (rawGender.isBlank()) return null
            return when (rawGender.trim().lowercase(Locale.ROOT)) {
                "female" -> Female
                "male" -> Male
                "other" -> Other
                else -> null
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun AiAgentInfoScreen(
    agent: AgentInfo,
    galleryItems: List<AgentImageGalleryItem>,
    navController: androidx.navigation.NavController,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val isDebugMode = HeartAppUtils.isAppDebugMode()
    val enableRemix = UiConfigs.ChatPage.enableRemix()
    val displayId = remember(agent.id, context) { formatDisplayId(agent.id, context = context) }

    // 为角色应援/Boost 功能
    val boostState by BoostManager.boostState.collectAsState()
    var showBoostSheet by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val showBoostError: (BoostError) -> Unit = { error ->
        val messageRes =
            when (error) {
                BoostError.NotEnoughPoints -> R.string.boost_toast_not_enough_points
                BoostError.DailyRewardAlreadyClaimed -> R.string.boost_daily_reward_already
                else -> R.string.boost_toast_generic_error
            }
        ToastUtils.showShort(messageRes)
    }

    Box(modifier = Modifier.fillMaxSize()) {
        AgentBackground(
            agentInfo = agent,
            modifier = Modifier.fillMaxSize(),
            showGradients = false, // 角色主页不需要渐变遮罩
        )

        Scaffold(
            modifier = Modifier.fillMaxSize(),
            containerColor = Color.Transparent,
            topBar = {
                CenterAlignedTopAppBar(
                    colors =
                        TopAppBarDefaults.topAppBarColors()
                            .copy(containerColor = Color.Transparent),
                    title = {},
                    navigationIcon = {
                        Image(
                            modifier =
                                Modifier.padding(horizontal = 12.dp).noRippleClickable { onBack() },
                            painter = painterResource(R.drawable.back),
                            contentDescription = null,
                        )
                    },
                    actions = {
                        if (enableRemix) {
                            Box(
                                modifier =
                                    Modifier.padding(horizontal = 12.dp)
                                        .size(36.dp)
                                        .clip(CircleShape)
                                        .background(Color.Black.copy(alpha = 0.35f))
                                        .noRippleClickable {
                                            ToastUtils.showShort(
                                                R.string.str_remix_feature_under_construction
                                            )
                                        },
                                contentAlignment = Alignment.Center,
                            ) {
                                Icon(
                                    imageVector = Icons.Rounded.AutoAwesome,
                                    contentDescription =
                                        stringResource(
                                            R.string.str_remix_feature_under_construction
                                        ),
                                    tint = Color.White,
                                )
                            }
                        }
                    },
                )
            },
        ) { innerPadding ->
            Column {
                // 顶部渐变遮罩
                Box(
                    modifier =
                        Modifier.fillMaxWidth()
                            .height(160.dp)
                            .background(
                                brush =
                                    Brush.verticalGradient(
                                        listOf(Color(0xFF000000), Color(0x00000000))
                                    )
                            )
                )
                Box(modifier = Modifier.fillMaxWidth().weight(1f))
                Box(
                    modifier =
                        Modifier.fillMaxWidth()
                            .background(
                                brush =
                                    Brush.verticalGradient(
                                        listOf(
                                            Color(0x00000000),
                                            HeartColor.primaryColor.copy(.3f),
                                            HeartColor.primaryColor.copy(.7f),
                                            HeartColor.primaryColor.copy(.9f),
                                            HeartColor.primaryColor,
                                            HeartColor.primaryColor,
                                        ),
                                        endY = 900f,
                                    )
                            )
                ) {
                    Column(
                        modifier =
                            Modifier.padding(innerPadding).verticalScroll(rememberScrollState())
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                val genderPronoun =
                                    remember(agent.gender) { AgentGenderPronoun.from(agent.gender) }
                                Row(
                                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                ) {
                                    Text(
                                        modifier = Modifier.weight(1f),
                                        text = agent.name,
                                        fontSize = 20.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        color = Color.White,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                }
                            }
                            Spacer(Modifier.width(16.dp))
                        }

                        // 角色应援/Boost 功能
                        Spacer(Modifier.height(16.dp))

                        BoostStatusChip(
                            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                            availablePoints = boostState.availablePoints,
                            onClick = {
                                if (boostState.availablePoints < BoostConfig.BOOST_STEP_POINTS) {
                                    ToastUtils.showShort(R.string.boost_toast_not_enough_points)
                                } else {
                                    showBoostSheet = true
                                }
                            },
                        )

                        Spacer(Modifier.height(16.dp))

                        Spacer(Modifier.height(24.dp))

                        Column(
                            modifier =
                                Modifier.padding(horizontal = 16.dp)
                                    .fillMaxWidth()
                                    .border(
                                        brush =
                                            Brush.linearGradient(
                                                colors =
                                                    listOf(
                                                        Color.Transparent,
                                                        Color.White.copy(0.2f),
                                                        Color.Transparent,
                                                    )
                                            ),
                                        width = 1.dp,
                                        shape = RoundedCornerShape(8.dp),
                                    )
                                    .background(
                                        color = Color(0x3378599A),
                                        shape = RoundedCornerShape(8.dp),
                                    )
                        ) {
                            Spacer(Modifier.height(16.dp))
                            Text(
                                modifier = Modifier.padding(horizontal = 12.dp),
                                text = stringResource(R.string.introduction),
                                fontSize = UiConfigs.CharacterIntroduction.TITLE_FONT_SIZE.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color.White,
                            )
                            Spacer(Modifier.height(8.dp))
                            Column(modifier = Modifier.animateContentSize()) {
                                var isExpanded by remember { mutableStateOf(false) }
                                var expandVisible by remember { mutableStateOf(false) }

                                // 使用智能 Tags 布局
                                val gender =
                                    runCatching {
                                            val tmpGender = agent.gender.lowercase()
                                            tmpGender.replaceFirst(
                                                tmpGender.first(),
                                                tmpGender.first().uppercase().first(),
                                            )
                                        }
                                        .getOrNull() ?: ""

                                val agentTags =
                                    mutableListOf(
                                        // FEMALE/MALE转化为Female/Male
                                        stringResource(R.string.gender_tag_format, gender)
                                    )
                                // 取10个即可，避免太多，因为设计也只需要显示一行
                                agent.tags?.take(10)?.forEach { tag ->
                                    tag?.let { agentTags.add(tag) }
                                }
                                SmartTagsLayout(
                                    tags = agentTags,
                                    modifier = Modifier.padding(horizontal = 12.dp),
                                    maxLines = 1,
                                )
                                Spacer(Modifier.height(4.dp))
                                Text(
                                    modifier = Modifier.padding(horizontal = 12.dp),
                                    text = agent.intro,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Light,
                                    color = Color.White,
                                    maxLines = if (isExpanded) Int.MAX_VALUE else 3,
                                    overflow = TextOverflow.Ellipsis,
                                    onTextLayout = {
                                        expandVisible = it.hasVisualOverflow || it.lineCount > 3
                                    },
                                )

                                if (expandVisible) {
                                    Button(
                                        onClick = { isExpanded = !isExpanded },
                                        contentPadding = PaddingValues(),
                                        colors =
                                            ButtonDefaults.buttonColors(
                                                containerColor = Color.Transparent
                                            ),
                                        modifier = Modifier.fillMaxWidth().height(16.dp),
                                    ) {
                                        Image(
                                            imageVector =
                                                if (isExpanded) {
                                                    Icons.Rounded.ArrowDropUp
                                                } else {
                                                    Icons.Rounded.ArrowDropDown
                                                },
                                            contentDescription = null,
                                            colorFilter = ColorFilter.tint(Color.White),
                                        )
                                    }
                                } else {
                                    Spacer(Modifier.height(12.dp))
                                }
                            }
                        }
                        if (galleryItems.isNotEmpty()) {
                            Spacer(Modifier.height(16.dp))
                            PhotoAlbumPreviewSection(
                                modifier =
                                    Modifier.padding(
                                        horizontal = UiConfigs.Padding.ScreenHorizontal
                                    ),
                                images = galleryItems,
                                agentId = agent.id,
                                onNavigateToPhotoAlbum = {
                                    navController.navigate(AgentInfoRoutes.photoAlbum(agent.id))
                                },
                            )
                        }
                        if (isDebugMode) {
                            Spacer(Modifier.height(60.dp))
                            Spacer(Modifier.height(24.dp))
                            AgentInfoDebugSection(agent = agent)
                        }
                    }
                }
            }
        }
    }

    // Boost Sheet 弹窗
    // 显示位置：角色主页（AgentInfoScreen）底部，以半屏弹窗形式展示
    // 显示时机：
    //   1. 用户点击了角色主页中的 BoostStatusChip，且可用积分 >= 100 pts
    //   2. 此时 showBoostSheet 被设置为 true，触发此弹窗显示
    // UI 效果：半屏底部弹窗，包含：
    //   - 当前角色的 Boost 信息
    //   - 可用积分显示
    //   - 积分投入滑条/步进器（每步 100 pts）
    //   - Boost 确认按钮
    // 交互流程：
    //   - 用户点击 BoostStatusChip → 打开此弹窗
    //   - 用户选择投入积分并确认 → 执行 Boost 操作 → 显示成功 Toast → 关闭弹窗
    //   - 用户点击关闭/取消 → 关闭弹窗
    if (showBoostSheet) {
        BoostSheet(
            agentInfo = agent,
            availablePoints = boostState.availablePoints,
            onBoostConfirmed = { points ->
                scope.launch {
                    try {
                        val result = BoostManager.boostAgent(agent, points)
                        ToastUtils.showShort(
                            context.getString(
                                R.string.boost_toast_success_points,
                                result.pointsSpent,
                                agent.name,
                            )
                        )
                        showBoostSheet = false
                    } catch (e: BoostException) {
                        showBoostError(e.error)
                        showBoostSheet = false
                    } catch (_: Exception) {
                        showBoostError(BoostError.NotEnoughPoints)
                        showBoostSheet = false
                    }
                }
            },
            onDismiss = { showBoostSheet = false },
        )
    }
}

/** 角色主页中生成图片的分区；用于展示聊天过程中产生图片的缩略图，并且可以点击进入详情页面 查看所有图片，位于 PhotoAlbumScreen.kt */
@Composable
private fun PhotoAlbumPreviewSection(
    modifier: Modifier = Modifier,
    images: List<AgentImageGalleryItem>,
    agentId: String,
    onNavigateToPhotoAlbum: () -> Unit,
    columnCount: Int = UiConfigs.ChatPage.PhotoAlbum.Preview.COLUMN_COUNT,
) {
    var previewImage by remember { mutableStateOf<String?>(null) }
    val displayedImages = images.take(columnCount)

    Column(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = stringResource(R.string.agent_photo_album_title),
                fontSize = UiConfigs.ChatPage.PhotoAlbum.Preview.TitleFontSize,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
            Text(
                text = stringResource(R.string.agent_photo_album_see_all),
                fontSize = UiConfigs.ChatPage.PhotoAlbum.Preview.SeeAllFontSize,
                fontWeight = FontWeight.Medium,
                color =
                    Color.White.copy(alpha = UiConfigs.ChatPage.PhotoAlbum.Preview.SeeAllTextAlpha),
                modifier = Modifier.noRippleClickable { onNavigateToPhotoAlbum() },
            )
        }
        Spacer(Modifier.height(UiConfigs.CharacterGallery.SectionSpacing))
        if (displayedImages.isNotEmpty()) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement =
                    Arrangement.spacedBy(UiConfigs.CharacterGallery.ImageSpacing),
            ) {
                displayedImages.forEach { item ->
                    AgentGalleryImageCardCompact(
                        item = item,
                        agentId = agentId,
                        onPreview = { previewImage = it },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
        }
        Spacer(Modifier.height(UiConfigs.CharacterGallery.SectionBottomPadding))
    }

    if (previewImage != null) {
        Dialog(
            onDismissRequest = { previewImage = null },
            properties =
                DialogProperties(
                    usePlatformDefaultWidth = false,
                    dismissOnClickOutside = true,
                    dismissOnBackPress = true,
                ),
        ) {
            val currentImageUrl = previewImage.orEmpty()
            FullScreenImageViewer(
                imageUrl = currentImageUrl,
                onDismiss = { previewImage = null },
                onAction = {
                    if (agentId.isNotBlank() && currentImageUrl.isNotBlank()) {
                        IntySetting.setChatBackgroundImage(agentId, currentImageUrl)
                        ToastUtils.showShort(R.string.agent_gallery_background_set_success)
                        previewImage = null
                    }
                },
                actionLabel = stringResource(R.string.agent_gallery_set_as_background),
            )
        }
    }
}

@Composable
private fun AgentGalleryImageCard(
    item: AgentImageGalleryItem,
    agentId: String,
    onPreview: (String) -> Unit,
) {
    val context = LocalContext.current
    val aspectRatio = if (item.height > 0) item.width.toFloat() / item.height.toFloat() else 1f
    var showResetDialog by remember { mutableStateOf(false) }
    // 直接计算，不使用 remember，确保在设置变化时能正确更新
    val isCurrentBackground = IntySetting.getChatBackgroundImage(agentId) == item.imageUrl

    Box(
        modifier =
            Modifier.width(UiConfigs.CharacterGallery.ImageWidth)
                .clip(RoundedCornerShape(UiConfigs.CharacterGallery.ImageCornerRadius))
                .background(Color.White.copy(alpha = 0.08f))
                .pointerInput(agentId, item.imageUrl, isCurrentBackground) {
                    detectTapGestures(
                        onTap = { onPreview(item.imageUrl) },
                        onLongPress = {
                            if (isCurrentBackground) {
                                showResetDialog = true
                            }
                        },
                    )
                }
    ) {
        AsyncImage(
            modifier = Modifier.fillMaxWidth().aspectRatio(aspectRatio),
            model =
                ImageRequest.Builder(context)
                    .data(
                        getCdnImageUrl(
                            item.imageUrl,
                            width = UiConfigs.CharacterGallery.CDN_IMAGE_WIDTH,
                            quality = UiConfigs.CharacterGallery.CDN_IMAGE_QUALITY,
                        )
                    )
                    .build(),
            contentDescription =
                stringResource(R.string.agent_gallery_ai_images_content_description),
            contentScale = ContentScale.Crop,
        )

        // 如果这是当前背景，显示一个小指示器
        if (isCurrentBackground) {
            Box(
                modifier =
                    Modifier.align(Alignment.TopEnd)
                        .padding(8.dp)
                        .size(16.dp)
                        .clip(CircleShape)
                        .background(ai.sxwl.android.design.theme.AppColors.Green500)
            )
        }
    }

    // 长按重置对话框
    // TODO：可以考虑删除，聚焦在设置背景功能上，长按的上下文按钮需求不大。
    if (showResetDialog) {
        AlertDialog(
            onDismissRequest = { showResetDialog = false },
            title = {
                Text(
                    text = stringResource(R.string.agent_gallery_reset_background),
                    color = Color.White,
                )
            },
            text = { Text(text = stringResource(R.string.are_you_sure), color = Color.White) },
            confirmButton = {
                TextButton(
                    onClick = {
                        IntySetting.clearChatBackgroundImage(agentId)
                        ToastUtils.showShort(R.string.agent_gallery_background_reset_success)
                        showResetDialog = false
                    }
                ) {
                    Text(text = stringResource(R.string.str_reset), color = Color.White)
                }
            },
            dismissButton = {
                TextButton(onClick = { showResetDialog = false }) {
                    Text(text = stringResource(R.string.cancel), color = Color.White)
                }
            },
            containerColor = Color(0xFF1E1E1E),
        )
    }
}

/**
 * 紧凑型角色相册图片卡片组件
 *
 * 使用场景：
 * - 在角色信息页面（AgentInfoScreen）的相册预览区域使用
 * - 通过 [PhotoAlbumPreviewSection] 以网格形式展示（默认 2 列）
 * - 用于在有限空间内紧凑展示角色的 AI 生成图片
 * - 与 [AgentGalleryImageCard] 相比，去掉了长按功能，更适合网格布局
 *
 * 视觉效果：
 * - 紧凑的卡片设计：使用 `fillMaxWidth()` 和 `weight(1f)` 自适应网格布局
 * - 圆角矩形卡片：使用 [UiConfigs.CharacterGallery.ImageCornerRadius] 配置的圆角半径
 * - 半透明背景：白色背景，透明度 0.08，提供微妙的卡片边界感
 * - 保持原始宽高比：根据图片的 width/height 计算 aspectRatio，确保图片不变形
 * - 图片裁剪填充：使用 `ContentScale.Crop` 裁剪填充整个卡片区域
 * - 背景状态指示器：如果图片被设置为当前角色的聊天背景，右上角显示 16dp 的绿色圆点指示器
 * - CDN 优化加载：通过 [getCdnImageUrl] 使用 CDN 优化图片加载性能
 *
 * 交互行为：
 * - 点击卡片：打开全屏预览对话框（[FullScreenImageViewer]），可查看大图并设置为聊天背景
 */
@Composable
private fun AgentGalleryImageCardCompact(
    item: AgentImageGalleryItem,
    agentId: String,
    onPreview: (String) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val aspectRatio = if (item.height > 0) item.width.toFloat() / item.height.toFloat() else 1f
    val isCurrentBackground = IntySetting.getChatBackgroundImage(agentId) == item.imageUrl

    Box(
        modifier =
            modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(UiConfigs.CharacterGallery.ImageCornerRadius))
                .background(
                    Color.White.copy(
                        alpha = UiConfigs.ChatPage.PhotoAlbum.Preview.ImageCardBackgroundAlpha
                    )
                )
                .pointerInput(agentId, item.imageUrl) {
                    detectTapGestures(onTap = { onPreview(item.imageUrl) })
                }
    ) {
        AsyncImage(
            modifier = Modifier.fillMaxWidth().aspectRatio(aspectRatio),
            model =
                ImageRequest.Builder(context)
                    .data(
                        getCdnImageUrl(
                            item.imageUrl,
                            width = UiConfigs.CharacterGallery.CDN_IMAGE_WIDTH,
                            quality = UiConfigs.CharacterGallery.CDN_IMAGE_QUALITY,
                        )
                    )
                    .build(),
            contentDescription =
                stringResource(R.string.agent_gallery_ai_images_content_description),
            contentScale = ContentScale.Crop,
        )

        if (isCurrentBackground) {
            Box(
                modifier =
                    Modifier.align(Alignment.TopEnd)
                        .padding(UiConfigs.ChatPage.PhotoAlbum.Preview.BackgroundIndicatorPadding)
                        .size(UiConfigs.ChatPage.PhotoAlbum.Preview.BackgroundIndicatorSize)
                        .clip(CircleShape)
                        .background(UiConfigs.ChatPage.PhotoAlbum.Preview.BackgroundIndicatorColor)
            )
        }
    }
}

@Composable
private fun AgentSpacerLine() {
    Spacer(Modifier.height(4.dp))
    Box(
        modifier =
            Modifier.fillMaxWidth()
                .height(1.dp)
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        )
                )
    ) {}
    Spacer(Modifier.height(4.dp))
}

@Composable
private fun AgentInfoDebugSection(agent: AgentInfo) {
    SelectionContainer {
        Column(
            modifier =
                Modifier.padding(horizontal = 16.dp)
                    .fillMaxWidth()
                    .border(
                        brush =
                            Brush.linearGradient(
                                listOf(
                                    Color.Transparent,
                                    Color.White.copy(alpha = 0.25f),
                                    Color.Transparent,
                                )
                            ),
                        width = 1.dp,
                        shape = RoundedCornerShape(8.dp),
                    )
                    .background(color = Color(0x4D000000), shape = RoundedCornerShape(8.dp))
        ) {
            Text(
                modifier = Modifier.padding(horizontal = 12.dp, vertical = 14.dp),
                text = "Debug · AgentInfo",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
            AgentSpacerLine()
            val debugItems =
                remember(agent) {
                    listOf(
                        "id" to agent.id,
                        "name" to agent.name,
                        "readableId" to agent.readableId,
                        "avatar" to agent.avatar,
                        "background" to agent.background,
                        "backgroundAnimatedUrl" to agent.backgroundAnimatedUrl,
                        "backgroundImages" to agent.backgroundImages.joinToString(),
                        "category" to agent.category,
                        "gender" to agent.gender,
                        "isFollowed" to agent.isFollowed.toString(),
                        "intro" to agent.intro,
                        "opening" to agent.opening,
                        "opening_audio_url" to agent.opening_audio_url,
                        "voicePreview" to agent.voicePreview,
                        "createdAt" to agent.createdAt,
                        "creator" to (agent.creator?.toString() ?: "null"),
                        "tags" to (agent.tags?.joinToString { it ?: "null" } ?: "null"),
                        "settings" to (agent.settings?.toString() ?: "null"),
                        "visibility" to agent.visibility,
                        "prompt" to agent.prompt,
                        "followerCount" to agent.followerCount.toString(),
                        "connectorCount" to agent.connectorCount.toString(),
                        "deletedAt" to (agent.deletedAt?.toString() ?: "null"),
                        "isDeleted(local)" to agent.isDeleted.toString(),
                    )
                }
            debugItems.forEachIndexed { index, (label, value) ->
                DebugInfoRow(label = label, value = value)
                if (index != debugItems.lastIndex) {
                    AgentSpacerLine()
                }
            }
            Spacer(Modifier.height(12.dp))
        }
    }
}

@Composable
private fun DebugInfoRow(label: String, value: String) {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp)) {
        Text(
            text = label,
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White.copy(alpha = 0.75f),
        )
        Spacer(Modifier.height(4.dp))
        Text(
            text = value.ifEmpty { "(empty)" },
            fontSize = 12.sp,
            fontWeight = FontWeight.Light,
            color = Color.White,
        )
    }
}

@Preview
@Composable
private fun PreviewAgentInfoScreen() {
    val navController = rememberNavController()
    val agent =
        AgentInfo(
            avatar = "",
            background = "",
            category = "category",
            gender = "Female",
            readableId = "readableID",
            isFollowed = true,
            name = "小甜甜",
            opening =
                "青青河边草，又有到海角，野火烧不尽，天涯也不到，啦啦啦啦啦，啦啦啦啦，啦啦啦啦，啦啦啦啦啦啦，轻轻河边草，又有到海角，野火烧不尽，春风吹不到。哈哈哈哈。",
            intro = "自我介绍，这是一个，什么可以说的呢，不知道，小甜甜就是小甜甜",
            prompt = "性感，时尚，火辣，大方",
        )

    val gallery =
        listOf(
            AgentImageGalleryItem(
                messageId = "1",
                imageUrl = "https://example.com/demo1.png",
                width = 512,
                height = 768,
                timestamp = null,
            ),
            AgentImageGalleryItem(
                messageId = "2",
                imageUrl = "https://example.com/demo2.png",
                width = 512,
                height = 512,
                timestamp = null,
            ),
        )

    AiAgentInfoScreen(
        agent = agent,
        galleryItems = gallery,
        navController = navController,
        onBack = {},
    )
}
