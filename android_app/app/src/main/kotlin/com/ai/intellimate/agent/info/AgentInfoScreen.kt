package com.ai.intellimate.agent.info

import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.utils.ToastUtils
import android.content.ClipData
import android.content.ClipboardManager
import androidx.annotation.StringRes
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material.icons.rounded.AutoAwesome
import androidx.compose.material3.AlertDialog
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
import androidx.navigation.compose.rememberNavController
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
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
import androidx.core.content.getSystemService
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostConfig
import com.ai.intellimate.boost.BoostError
import com.ai.intellimate.boost.BoostException
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.boost.BoostState
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
    val boostState by
        if (isDebugMode) BoostManager.boostState.collectAsState()
        else remember { mutableStateOf(BoostState()) }
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
                                    genderPronoun?.let {
                                        Spacer(Modifier.width(8.dp))
                                        Text(
                                            text = stringResource(id = it.labelRes),
                                            fontSize = 14.sp,
                                            fontWeight = FontWeight.Medium,
                                            color = Color.White.copy(alpha = 0.85f),
                                        )
                                    }
                                }
                                Spacer(Modifier.height(5.dp))
                                Row(
                                    modifier =
                                        Modifier.fillMaxWidth().noRippleClickable {
                                            if (agent.id.isBlank()) {
                                                return@noRippleClickable
                                            }
                                            val clipboard =
                                                context.getSystemService<ClipboardManager>()
                                            clipboard?.setPrimaryClip(
                                                ClipData.newPlainText(
                                                    CLIPBOARD_LABEL_AGENT_ID,
                                                    agent.id,
                                                )
                                            )
                                            if (clipboard != null) {
                                                ToastUtils.showShort(
                                                    R.string.toast_copied_to_clipboard
                                                )
                                            }
                                        },
                                    verticalAlignment = Alignment.CenterVertically,
                                ) {
                                    Spacer(Modifier.width(16.dp))
                                    Text(
                                        modifier = Modifier.fillMaxWidth(),
                                        text = stringResource(R.string.ID, displayId),
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Light,
                                        color = Color.White.copy(0.55f),
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                }
                            }

                            Spacer(Modifier.width(16.dp))
                        }

                        // 角色应援/Boost 功能（仅在 debug 模式下显示）
                        if (isDebugMode) {
                            Spacer(Modifier.height(16.dp))

                            BoostStatusChip(
                                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                                availablePoints = boostState.availablePoints,
                                onClick = {
                                    if (
                                        boostState.availablePoints < BoostConfig.BOOST_STEP_POINTS
                                    ) {
                                        ToastUtils.showShort(R.string.boost_toast_not_enough_points)
                                    } else {
                                        showBoostSheet = true
                                    }
                                },
                            )

                            Spacer(Modifier.height(16.dp))
                        }

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
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color.White,
                            )
                            Spacer(Modifier.height(12.dp))
                            Column {
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
                                Spacer(Modifier.height(8.dp))
                                Text(
                                    modifier = Modifier.padding(horizontal = 12.dp),
                                    text = agent.intro,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Light,
                                    color = Color.White,
                                    maxLines = 3,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }

                            Spacer(Modifier.height(12.dp))
                            AgentSpacerLine()
                            Spacer(Modifier.height(10.dp))
                            Text(
                                modifier = Modifier.padding(horizontal = 12.dp),
                                text = stringResource(R.string.opening),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color.White,
                            )
                            Spacer(Modifier.height(12.dp))
                            Text(
                                modifier = Modifier.padding(horizontal = 12.dp),
                                text = agent.opening,
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Light,
                                color = Color.White,
                                maxLines = 3,
                                overflow = TextOverflow.Ellipsis,
                            )
                        }
                        if (galleryItems.isNotEmpty()) {
                            Spacer(Modifier.height(16.dp))
                            AgentGeneratedImagesSection(
                                modifier = Modifier.padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
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

    // Boost Sheet 弹窗（仅在 debug 模式下显示）
    // 显示位置：角色主页（AgentInfoScreen）底部，以半屏弹窗形式展示
    // 显示时机：
    //   1. 必须在 debug 模式下（isDebugMode == true）
    //   2. 用户点击了角色主页中的 BoostStatusChip（第 291-301 行），且可用积分 >= 100 pts
    //   3. 此时 showBoostSheet 被设置为 true，触发此弹窗显示
    // UI 效果：半屏底部弹窗，包含：
    //   - 当前角色的 Boost 信息
    //   - 可用积分显示
    //   - 积分投入滑条/步进器（每步 100 pts）
    //   - Boost 确认按钮
    // 交互流程：
    //   - 用户点击 BoostStatusChip → 打开此弹窗
    //   - 用户选择投入积分并确认 → 执行 Boost 操作 → 显示成功 Toast → 关闭弹窗
    //   - 用户点击关闭/取消 → 关闭弹窗
    if (isDebugMode && showBoostSheet) {
        BoostSheet(
            agentInfo = agent,
            availablePoints = boostState.availablePoints,
            onBoostConfirmed = { points ->
                scope.launch {
                    try {
                        val result = BoostManager.boostAgent(agent, points)
                        ToastUtils.showShort(
                            context.getString(R.string.boost_toast_success, agent.name)
                        )
                        showBoostSheet = false
                    } catch (e: BoostException) {
                        showBoostError(e.error)
                        showBoostSheet = false
                    } catch (e: Exception) {
                        showBoostError(BoostError.NotEnoughPoints)
                        showBoostSheet = false
                    }
                }
            },
            onDismiss = { showBoostSheet = false },
        )
    }
}

@Composable
private fun AgentGeneratedImagesSection(
    modifier: Modifier = Modifier,
    images: List<AgentImageGalleryItem>,
    agentId: String,
    onNavigateToPhotoAlbum: () -> Unit,
    columnCount: Int = 2,
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
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
            Text(
                text = stringResource(R.string.agent_photo_album_see_all),
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = Color.White.copy(alpha = 0.85f),
                modifier = Modifier.noRippleClickable { onNavigateToPhotoAlbum() },
            )
        }
        Spacer(Modifier.height(UiConfigs.CharacterGallery.SectionSpacing))
        if (displayedImages.isNotEmpty()) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(UiConfigs.CharacterGallery.ImageSpacing),
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
                        .background(Color(0xFF4CAF50))
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
                .background(Color.White.copy(alpha = 0.08f))
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
                        .padding(8.dp)
                        .size(16.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF4CAF50))
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
