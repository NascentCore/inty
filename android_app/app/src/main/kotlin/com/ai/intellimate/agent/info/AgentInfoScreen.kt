package com.ai.intellimate.agent.info

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.common.utils.HeartAppUtils
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.utils.ToastUtils
import android.content.ClipData
import android.content.ClipboardManager
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.getSystemService
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.chat.ui.FullScreenImageViewer
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.ui.components.AgentBackground
import com.ai.intellimate.ui.components.SmartTagsLayout
import com.ai.intellimate.utils.formatDisplayId

private const val CLIPBOARD_LABEL_AGENT_ID = "Agent ID"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun AiAgentInfoScreen(
    agent: AgentInfo,
    galleryItems: List<AgentImageGalleryItem>,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    val isDebugMode = HeartAppUtils.isAppDebugMode()
    var showBottomSheet by remember { mutableStateOf(false) }
    val bottomSheetState = rememberModalBottomSheetState()
    val displayId = remember(agent.id, context) { formatDisplayId(agent.id, context = context) }

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
                        Image(
                            modifier =
                                Modifier.padding(horizontal = 12.dp).noRippleClickable {
                                    showBottomSheet = true
                                },
                            painter = painterResource(R.drawable.icon_more2),
                            contentDescription = null,
                        )
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
                                Text(
                                    modifier = Modifier.padding(start = 16.dp),
                                    text = agent.name,
                                    fontSize = 20.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = Color.White,
                                )
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

                            Spacer(Modifier.height(16.dp))
                        }
                        if (galleryItems.isNotEmpty()) {
                            Spacer(Modifier.height(16.dp))
                            AgentGeneratedImagesSection(
                                modifier = Modifier.padding(horizontal = 16.dp),
                                images = galleryItems,
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

    // 底部菜单
    if (showBottomSheet) {
        ModalBottomSheet(
            onDismissRequest = { showBottomSheet = false },
            sheetState = bottomSheetState,
            containerColor = HeartColor.primaryColor,
            contentColor = Color.White,
        ) {
            BottomSheetContent(
                onReportClick = {
                    showBottomSheet = false
                    // 检查是否已登录
                    if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                        ReportActivity.Companion.launch(context, agent.id, "AGENT")
                    }
                },
                onCancelClick = { showBottomSheet = false },
            )
        }
    }
}

private object AgentGalleryConfig {
    val SectionSpacing = 12.dp
    val SectionTitleSpacing = 4.dp
    val ImageSpacing = 12.dp
    val ImageWidth = 140.dp
    val ImageCornerRadius = 14.dp
    val SectionBottomPadding = 8.dp
    const val CDN_IMAGE_WIDTH = 480
    const val CDN_IMAGE_QUALITY = 70
}

@Composable
private fun AgentGeneratedImagesSection(modifier: Modifier = Modifier, images: List<AgentImageGalleryItem>) {
    var previewImage by remember { mutableStateOf<String?>(null) }

    Column(modifier = modifier.fillMaxWidth()) {
        Text(
            text = stringResource(R.string.agent_gallery_ai_images_title),
            fontSize = 16.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
        Spacer(Modifier.height(AgentGalleryConfig.SectionTitleSpacing))
        Text(
            text = stringResource(R.string.agent_gallery_ai_images_description, images.size),
            fontSize = 12.sp,
            color = Color.White.copy(alpha = 0.7f),
        )
        Spacer(Modifier.height(AgentGalleryConfig.SectionSpacing))
        LazyRow(horizontalArrangement = Arrangement.spacedBy(AgentGalleryConfig.ImageSpacing)) {
            items(images, key = { it.messageId }) { item ->
                AgentGalleryImageCard(item = item) { previewImage = it }
            }
        }
        Spacer(Modifier.height(AgentGalleryConfig.SectionBottomPadding))
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
            FullScreenImageViewer(imageUrl = previewImage.orEmpty(), onDismiss = { previewImage = null })
        }
    }
}

@Composable
private fun AgentGalleryImageCard(item: AgentImageGalleryItem, onPreview: (String) -> Unit) {
    val context = LocalContext.current
    val aspectRatio =
        if (item.height > 0) item.width.toFloat() / item.height.toFloat() else 1f
    Box(
        modifier =
            Modifier.width(AgentGalleryConfig.ImageWidth)
                .clip(RoundedCornerShape(AgentGalleryConfig.ImageCornerRadius))
                .background(Color.White.copy(alpha = 0.08f))
                .noRippleClickable { onPreview(item.imageUrl) },
    ) {
        AsyncImage(
            modifier = Modifier.fillMaxWidth().aspectRatio(aspectRatio),
            model =
                ImageRequest.Builder(context)
                    .data(
                        getCdnImageUrl(
                            item.imageUrl,
                            width = AgentGalleryConfig.CDN_IMAGE_WIDTH,
                            quality = AgentGalleryConfig.CDN_IMAGE_QUALITY,
                        )
                    )
                    .build(),
            contentDescription =
                stringResource(R.string.agent_gallery_ai_images_content_description),
            contentScale = ContentScale.Crop,
        )
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
private fun BottomSheetContent(onReportClick: () -> Unit, onCancelClick: () -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 24.dp)) {
        // Report按钮
        Button(
            onClick = onReportClick,
            modifier = Modifier.fillMaxWidth().height(60.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0x3378599A)),
            shape = RoundedCornerShape(16.dp),
        ) {
            Text(
                text = stringResource(R.string.str_report),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Normal,
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Cancel按钮
        Button(
            onClick = onCancelClick,
            modifier = Modifier.fillMaxWidth().height(60.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0x3378599A)),
            shape = RoundedCornerShape(16.dp),
        ) {
            Text(
                text = stringResource(R.string.cancel_button),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Normal,
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
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
                    .background(
                        color = Color(0x4D000000),
                        shape = RoundedCornerShape(8.dp),
                    )
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

        AiAgentInfoScreen(agent = agent, galleryItems = gallery) {}
}
