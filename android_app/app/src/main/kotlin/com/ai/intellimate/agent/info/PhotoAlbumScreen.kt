package com.ai.intellimate.agent.info

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.chat.ui.FullScreenImageViewer
import com.ai.intellimate.ui.UiConfigs

/**
 * 这是角色相册的单独页面，是通过角色主页的 生图预览区右上角 See All 进入的页面
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun PhotoAlbumScreen(
    agent: AgentInfo,
    galleryItems: List<AgentImageGalleryItem>,
    onBack: () -> Unit,
) {
    var previewImage by remember { mutableStateOf<String?>(null) }

    Box(modifier = Modifier.fillMaxSize()) {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            containerColor = Color.Transparent,
            topBar = {
                CenterAlignedTopAppBar(
                    colors =
                        TopAppBarDefaults.topAppBarColors()
                            .copy(containerColor = Color.Transparent),
                    title = {
                        Text(
                            text = stringResource(R.string.agent_photo_album_title),
                            color = Color.White,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                    },
                    navigationIcon = {
                        IconButton(onClick = onBack) {
                            Image(
                                modifier = Modifier.size(24.dp),
                                painter = painterResource(R.drawable.back),
                                contentDescription = null,
                            )
                        }
                    },
                )
            },
        ) { innerPadding ->
            Box(
                modifier =
                    Modifier.fillMaxSize()
                        .background(
                            brush =
                                androidx.compose.ui.graphics.Brush.verticalGradient(
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
                if (galleryItems.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(
                            text = "No images available",
                            color = Color.White.copy(alpha = 0.7f),
                            fontSize = 14.sp,
                        )
                    }
                } else {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(UiConfigs.ChatPage.PhotoAlbum.All.COLUMN_COUNT),
                        modifier =
                            Modifier.fillMaxSize()
                                .padding(innerPadding)
                                .padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
                        contentPadding = PaddingValues(vertical = 16.dp),
                        horizontalArrangement =
                            Arrangement.spacedBy(UiConfigs.MePage.GridHorizontalSpacing),
                        verticalArrangement =
                            Arrangement.spacedBy(UiConfigs.MePage.GridVerticalSpacing),
                    ) {
                        items(
                            items = galleryItems,
                            key = { item -> item.imageUrl },
                        ) { item ->
                            PhotoAlbumImageItem(
                                item = item,
                                agentId = agent.id,
                                onPreview = { previewImage = it },
                            )
                        }
                    }
                }
            }
        }
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
            FullScreenImageViewer(
                imageUrl = previewImage.orEmpty(),
                onDismiss = { previewImage = null },
            )
        }
    }
}

@Composable
private fun PhotoAlbumImageItem(
    item: AgentImageGalleryItem,
    agentId: String,
    onPreview: (String) -> Unit,
) {
    val context = LocalContext.current
    val aspectRatio = if (item.height > 0) item.width.toFloat() / item.height.toFloat() else 1f
    
    // 使用 remember 和 mutableStateOf 来跟踪当前背景状态，确保 UI 能够响应变化
    // 在点击时立即更新状态，确保 UI 能够立即响应
    var isCurrentBackground by remember { mutableStateOf(IntySetting.getChatBackgroundImage(agentId) == item.imageUrl) }
    
    // 在每次重组时重新检查背景状态，确保当其他图片被设为背景时，当前图片的状态也能正确更新
    // 使用 LaunchedEffect 来监听背景设置变化，当 agentId 或 item.imageUrl 变化时重新检查
    LaunchedEffect(agentId, item.imageUrl) {
        val currentBackground = IntySetting.getChatBackgroundImage(agentId)
        isCurrentBackground = currentBackground == item.imageUrl
    }
    
    // 在重组时也检查一次，确保状态同步
    // 使用 SideEffect 来在每次重组时检查背景状态，但只在状态不匹配时更新
    androidx.compose.runtime.SideEffect {
        val currentBackground = IntySetting.getChatBackgroundImage(agentId)
        val shouldBeBackground = currentBackground == item.imageUrl
        if (isCurrentBackground != shouldBeBackground) {
            isCurrentBackground = shouldBeBackground
        }
    }

    Column(
        modifier = Modifier.fillMaxWidth(),
    ) {
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.CharacterGallery.ImageCornerRadius))
                    .background(Color.White.copy(alpha = 0.08f))
                    .pointerInput(item.imageUrl) {
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
                contentDescription = stringResource(R.string.agent_gallery_ai_images_content_description),
                contentScale = ContentScale.Crop,
            )
        }

        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .padding(top = 8.dp)
                    .noRippleClickable {
                        if (isCurrentBackground) {
                            IntySetting.clearChatBackgroundImage(agentId)
                            isCurrentBackground = false
                            ToastUtils.showShort(R.string.agent_gallery_background_reset_success)
                        } else {
                            IntySetting.setChatBackgroundImage(agentId, item.imageUrl)
                            isCurrentBackground = true
                            ToastUtils.showShort(R.string.agent_gallery_background_set_success)
                        }
                    },
            contentAlignment = Alignment.Center,
        ) {
            if (isCurrentBackground) {
                Icon(
                    imageVector = Icons.Default.Check,
                    contentDescription = stringResource(R.string.agent_photo_album_set_as_background),
                    tint = Color.White,
                    modifier = Modifier.size(20.dp),
                )
            } else {
                Text(
                    text = stringResource(R.string.agent_photo_album_set_as_background),
                    fontSize = 12.sp,
                    color = Color.White.copy(alpha = 0.85f),
                    fontWeight = FontWeight.Medium,
                )
            }
        }
    }
}
