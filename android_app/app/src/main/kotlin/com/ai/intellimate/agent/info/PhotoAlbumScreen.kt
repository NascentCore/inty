package com.ai.intellimate.agent.info

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
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
import androidx.navigation.NavController
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.utils.ChatBackgroundUtils

/** 这是角色相册的单独页面，是通过角色主页的 生图预览区右上角 See All 进入的页面 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun PhotoAlbumScreen(
    navController: NavController,
    agent: AgentInfo,
    galleryItems: List<AgentImageGalleryItem>,
    onBack: () -> Unit,
) {
    var previewImage by remember { mutableStateOf<String?>(null) }
    var currentBackgroundUrl by remember {
        mutableStateOf<String?>(IntySetting.getChatBackgroundImage(agent.id))
    }

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
                            fontSize = UiConfigs.ChatPage.PhotoAlbum.All.TopBarTitleFontSize,
                            fontWeight = FontWeight.SemiBold,
                        )
                    },
                    navigationIcon = {
                        IconButton(onClick = onBack) {
                            Image(
                                modifier =
                                    Modifier.size(
                                        UiConfigs.ChatPage.PhotoAlbum.All.BackButtonIconSize
                                    ),
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
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        Text(
                            text = "No images available",
                            color =
                                Color.White.copy(
                                    alpha = UiConfigs.ChatPage.PhotoAlbum.All.EmptyStateTextAlpha
                                ),
                            fontSize = UiConfigs.ChatPage.PhotoAlbum.All.EmptyStateFontSize,
                        )
                    }
                } else {
                    LazyVerticalGrid(
                        columns = GridCells.Fixed(UiConfigs.ChatPage.PhotoAlbum.All.COLUMN_COUNT),
                        modifier =
                            Modifier.fillMaxSize()
                                .padding(innerPadding)
                                .padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
                        contentPadding =
                            PaddingValues(
                                vertical =
                                    UiConfigs.ChatPage.PhotoAlbum.All.GridContentVerticalPadding
                            ),
                        horizontalArrangement =
                            Arrangement.spacedBy(UiConfigs.MePage.GridHorizontalSpacing),
                        verticalArrangement =
                            Arrangement.spacedBy(UiConfigs.MePage.GridVerticalSpacing),
                    ) {
                        items(items = galleryItems, key = { item -> item.imageUrl }) { item ->
                            PhotoAlbumImageItem(
                                item = item,
                                agentId = agent.id,
                                currentBackgroundUrl = currentBackgroundUrl,
                                onBackgroundChanged = { newUrl -> currentBackgroundUrl = newUrl },
                                onPreview = { previewImage = it },
                            )
                        }
                    }
                }
            }
        }
    }

    AgentGalleryImagePreviewDialog(
        navController,
        previewImageUrl = previewImage,
        agentId = agent.id,
        onDismiss = { previewImage = null },
        onBackgroundChanged = { newUrl -> currentBackgroundUrl = newUrl },
    )
}

@Composable
private fun PhotoAlbumImageItem(
    item: AgentImageGalleryItem,
    agentId: String,
    currentBackgroundUrl: String?,
    onBackgroundChanged: (String?) -> Unit,
    onPreview: (String) -> Unit,
) {
    val context = LocalContext.current

    // 从共享状态派生当前背景状态，确保所有项目都能正确响应背景变化
    val isCurrentBackground = currentBackgroundUrl == item.imageUrl

    Column(modifier = Modifier.fillMaxWidth()) {
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.CharacterGallery.ImageCornerRadius))
                    .background(
                        Color.White.copy(
                            alpha = UiConfigs.ChatPage.PhotoAlbum.All.ImageCardBackgroundAlpha
                        )
                    )
                    .pointerInput(item.imageUrl) {
                        detectTapGestures(onTap = { onPreview(item.imageUrl) })
                    }
        ) {
            AsyncImage(
                modifier = Modifier.fillMaxWidth().aspectRatio(9f / 16f),
                model =
                    ImageRequest.Builder(context)
                        .data(
                            getCdnImageUrl(
                                item.imageUrl,
                                width = UiConfigs.CharacterProfile.CDN_STATIC_BACKGROUND_WIDTH,
                                quality = UiConfigs.CharacterProfile.CDN_IMAGE_QUALITY,
                            ) // 确保设置聊天背景后能使用相同url的缓存，以避免出现加载过程。
                        )
                        .build(),
                contentDescription =
                    stringResource(R.string.agent_gallery_ai_images_content_description),
                contentScale = ContentScale.Crop,
            )

            // 如果这是当前背景，显示绿色圆点指示器
            if (isCurrentBackground) {
                Box(
                    modifier =
                        Modifier.align(Alignment.TopEnd)
                            .padding(
                                UiConfigs.ChatPage.PhotoAlbum.Preview.BackgroundIndicatorPadding
                            )
                            .size(UiConfigs.ChatPage.PhotoAlbum.Preview.BackgroundIndicatorSize)
                            .clip(CircleShape)
                            .background(UiConfigs.ChatPage.PhotoAlbum.All.BackgroundIndicatorColor)
                )
            }
        }

        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .padding(top = UiConfigs.ChatPage.PhotoAlbum.All.ImageItemButtonTopPadding)
                    .noRippleClickable {
                        val newBackgroundUrl =
                            ChatBackgroundUtils.toggleChatBackground(
                                agentId,
                                item.imageUrl,
                                isCurrentBackground,
                            )
                        onBackgroundChanged(newBackgroundUrl)
                    },
            contentAlignment = Alignment.Center,
        ) {
            if (isCurrentBackground) {
                Icon(
                    imageVector = Icons.Default.Check,
                    contentDescription =
                        stringResource(R.string.agent_photo_album_set_as_background),
                    tint = Color.White,
                    modifier =
                        Modifier.size(UiConfigs.ChatPage.PhotoAlbum.All.ImageItemButtonIconSize),
                )
            } else {
                Text(
                    text = stringResource(R.string.agent_photo_album_set_as_background),
                    fontSize = UiConfigs.ChatPage.PhotoAlbum.All.ImageItemButtonTextFontSize,
                    color =
                        Color.White.copy(
                            alpha = UiConfigs.ChatPage.PhotoAlbum.All.ImageItemButtonTextAlpha
                        ),
                    fontWeight = FontWeight.Medium,
                )
            }
        }
    }
}
