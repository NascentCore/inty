package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.design.ImageLoaderUtils
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.rememberTransformableState
import androidx.compose.foundation.gestures.transformable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.ZoomIn
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostException
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.components.ReportButton
import com.ai.intellimate.utils.GalleryImageDownloadUtils
import com.ai.intellimate.utils.ShareUtils
import kotlinx.coroutines.launch

private val IMAGE_UPSCALE_FACTORS = listOf(1, 2, 4)
private const val IMAGE_VIEWER_UPSCALE_EVENT = "image_viewer_upscale"

/** 全屏图片查看器 */
@Composable
internal fun FullScreenImageViewer(
    imageUrl: String,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
    onAction: (() -> Unit)? = null,
    actionLabel: String? = null,
    onReport: (() -> Unit)? = null,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var isSavingToGallery by remember { mutableStateOf(false) }
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
    var selectedUpscaleFactor by remember { mutableIntStateOf(1) }
    var showUpscaleOptionsDialog by remember { mutableStateOf(false) }
    var showUpscaleCreditsDialog by remember { mutableStateOf(false) }
    var hasTemporaryUpscaleAccess by remember(imageUrl) { mutableStateOf(false) }
    var isDeductingUpscaleCredits by remember { mutableStateOf(false) }
    val canUseUpscaleFeature = vipStatus.isSubscribed || hasTemporaryUpscaleAccess
    val upscaleWidth =
        remember(selectedUpscaleFactor) {
            UiConfigs.CharacterProfile.CDN_STATIC_BACKGROUND_WIDTH * selectedUpscaleFactor
        }

    val cdnImageUrl =
        // 关键步骤：通过切换 CDN 宽度来提供 1x/2x/4x 放大选项。
        remember(imageUrl, upscaleWidth) {
            getCdnImageUrl(
                imageUrl,
                width = upscaleWidth,
                quality = UiConfigs.CharacterProfile.CDN_IMAGE_QUALITY,
            ) ?: imageUrl
        }

    fun trackUpscaleEvent(action: String, vararg extraParams: Pair<String, Any?>) {
        FirebaseManager.logEvent(
            IMAGE_VIEWER_UPSCALE_EVENT,
            FirebaseManager.safeEventParams(
                "action" to action,
                "is_subscribed" to vipStatus.isSubscribed,
                "has_temporary_access" to hasTemporaryUpscaleAccess,
                "current_factor" to selectedUpscaleFactor,
                "timestamp" to System.currentTimeMillis(),
                *extraParams,
            ),
        )
    }

    // 缩放、平移状态（不支持旋转）
    var scale by remember { mutableFloatStateOf(1f) }
    var offsetX by remember { mutableFloatStateOf(0f) }
    var offsetY by remember { mutableFloatStateOf(0f) }

    // 记录容器和图片的实际尺寸，用于计算平移边界
    var containerSize by remember { mutableStateOf(IntSize.Zero) }
    var imageSize by remember { mutableStateOf(IntSize.Zero) }

    // 计算平移边界约束
    // 当图片放大后，需要确保图片边缘不会离开屏幕边缘
    // 约束规则：图片边缘不能离开屏幕边缘
    fun calculateConstrainedOffset(
        currentOffset: Float,
        panChange: Float,
        containerSize: Float,
        imageSize: Float,
        currentScale: Float,
    ): Float {
        if (currentScale <= 1f) return 0f // 缩放为1时，不允许平移

        // 计算放大后图片的实际尺寸（原始显示尺寸 * 缩放比例）
        val scaledImageSize = imageSize * currentScale

        // 计算可平移的范围
        // 图片中心在容器中心，所以可平移的最大范围是图片超出容器的部分的一半
        // 如果缩放后图片小于容器，则不可平移
        val maxOffset =
            if (scaledImageSize > containerSize) {
                (scaledImageSize - containerSize) / 2f
            } else {
                0f
            }

        // 计算新的偏移量
        val newOffset = currentOffset + panChange

        // 约束在边界内：[-maxOffset, maxOffset]
        return newOffset.coerceIn(-maxOffset, maxOffset)
    }

    // 使用transformable手势处理缩放和平移（不允许旋转）
    // 注意：zoomChange 是相对于上一次调用的变化量，不是累积值
    val transformableState =
        rememberTransformableState(
            onTransformation = { zoomChange: Float, panChange: Offset, _: Float ->
                // 缩放：最小1倍，最大5倍（不可缩小）
                val newScale = (scale * zoomChange).coerceIn(1f, 5f)
                scale = newScale

                // 平移：只在缩放大于1倍时允许平移，并应用边界约束
                if (
                    newScale > 1f &&
                        containerSize.width > 0 &&
                        containerSize.height > 0 &&
                        imageSize.width > 0 &&
                        imageSize.height > 0
                ) {
                    // 计算约束后的平移偏移
                    offsetX =
                        calculateConstrainedOffset(
                            currentOffset = offsetX,
                            panChange = panChange.x,
                            containerSize = containerSize.width.toFloat(),
                            imageSize = imageSize.width.toFloat(),
                            currentScale = newScale,
                        )
                    offsetY =
                        calculateConstrainedOffset(
                            currentOffset = offsetY,
                            panChange = panChange.y,
                            containerSize = containerSize.height.toFloat(),
                            imageSize = imageSize.height.toFloat(),
                            currentScale = newScale,
                        )
                } else {
                    // 如果缩放回到1倍，重置平移
                    offsetX = 0f
                    offsetY = 0f
                }

                // 忽略旋转（rotationChange）
            }
        )

    Box(
        modifier =
            modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.95f))
                .onGloballyPositioned { coordinates -> containerSize = coordinates.size },
        contentAlignment = Alignment.Center,
    ) {
        // 图片
        AsyncImage(
            modifier =
                Modifier.fillMaxSize()
                    .onGloballyPositioned { coordinates ->
                        // 记录图片的实际显示尺寸（使用ContentScale.Fit后的尺寸）
                        imageSize = coordinates.size
                    }
                    .graphicsLayer(
                        scaleX = scale,
                        scaleY = scale,
                        translationX = offsetX,
                        translationY = offsetY,
                    )
                    .transformable(state = transformableState),
            model =
                ImageLoaderUtils.createDeviceAdaptiveImageRequest(
                    context = context,
                    imageUrl = cdnImageUrl,
                    maxWidth = 1920,
                    maxHeight = 1920,
                ),
            contentDescription = "Full screen image",
            contentScale = ContentScale.Fit,
            alignment = Alignment.Center,
        )

        // 顶部栏：左侧固定关闭按钮，右侧可横向滑动的操作按钮（避免覆盖关闭按钮或窄屏下压缩）
        Row(
            modifier =
                Modifier.align(Alignment.TopCenter)
                    .fillMaxWidth()
                    .padding(top = 8.dp, start = 8.dp, end = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = { onDismiss() }, modifier = Modifier.padding(8.dp)) {
                Text(
                    text = "✕",
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                )
            }

            // 操作按钮区域：宽度不足时可左右滑动，不压缩按钮、不覆盖关闭按钮
            Row(
                modifier =
                    Modifier.weight(1f)
                        .horizontalScroll(rememberScrollState())
                        .padding(start = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Box(
                    modifier =
                        Modifier.clip(RoundedCornerShape(8.dp))
                            .background(Color.Black.copy(alpha = 0.7f), RoundedCornerShape(8.dp))
                            .noRippleClickable {
                                if (ShareUtils.canShareAsUrl(cdnImageUrl)) {
                                    ShareUtils.shareUrl(
                                        context = context,
                                        url = cdnImageUrl,
                                        chooserTitle = context.getString(R.string.share_button),
                                    )
                                } else {
                                    ToastUtils.showShort(R.string.toast_no_shareable_image)
                                }
                            }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Filled.Share,
                            contentDescription =
                                stringResource(R.string.share_image_content_description),
                            modifier =
                                Modifier.size(UiConfigs.ChatPage.PhotoAlbum.Preview.ButtonIconSize),
                            tint = Color.White,
                        )
                        Text(
                            text = stringResource(R.string.share_button),
                            color = Color.White,
                            fontSize = UiConfigs.ChatPage.PhotoAlbum.Preview.ButtonTextFontSize,
                            fontWeight = FontWeight.Medium,
                        )
                    }
                }

                Box(
                    modifier =
                        Modifier.clip(RoundedCornerShape(8.dp))
                            .background(Color.Black.copy(alpha = 0.7f), RoundedCornerShape(8.dp))
                            .noRippleClickable {
                                trackUpscaleEvent("click_button")
                                if (canUseUpscaleFeature) {
                                    trackUpscaleEvent("open_options_dialog")
                                    showUpscaleOptionsDialog = true
                                } else {
                                    trackUpscaleEvent("open_unlock_dialog")
                                    showUpscaleCreditsDialog = true
                                }
                            }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Box(
                            modifier =
                                Modifier.size(UiConfigs.ChatPage.PhotoAlbum.Preview.ButtonIconSize)
                        ) {
                            Icon(
                                imageVector = Icons.Filled.ZoomIn,
                                contentDescription =
                                    stringResource(R.string.upscale_image_content_description),
                                modifier =
                                    Modifier.align(Alignment.Center)
                                        .size(UiConfigs.ChatPage.PhotoAlbum.Preview.ButtonIconSize),
                                tint = Color.White,
                            )
                            Image(
                                modifier =
                                    Modifier.align(Alignment.TopEnd)
                                        .padding(top = 5.dp, end = 1.dp),
                                painter = painterResource(R.drawable.ic_vip_badge),
                                contentDescription = null,
                            )
                        }
                        Text(
                            text = stringResource(R.string.upscale_button),
                            color = Color.White,
                            fontSize = UiConfigs.ChatPage.PhotoAlbum.Preview.ButtonTextFontSize,
                            fontWeight = FontWeight.Medium,
                        )
                    }
                }

                Box(
                    modifier =
                        Modifier.clip(RoundedCornerShape(8.dp))
                            .background(
                                if (isSavingToGallery) Color.Gray.copy(alpha = 0.5f)
                                else Color.Black.copy(alpha = 0.7f),
                                RoundedCornerShape(8.dp),
                            )
                            .noRippleClickable(enabled = !isSavingToGallery) {
                                if (isSavingToGallery) return@noRippleClickable
                                isSavingToGallery = true
                                scope.launch {
                                    val saveResult: Result<android.net.Uri>
                                    try {
                                        saveResult =
                                            GalleryImageDownloadUtils.saveImageUrlToGallery(
                                                context = context,
                                                imageUrl = cdnImageUrl,
                                            )
                                    } finally {
                                        isSavingToGallery = false
                                    }

                                    if (saveResult.isSuccess) {
                                        ToastUtils.showShort(R.string.toast_image_saved_to_album)
                                    } else {
                                        ToastUtils.showShort(R.string.toast_image_save_failed)
                                    }
                                }
                            }
                            .padding(horizontal = 12.dp, vertical = 8.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Filled.Download,
                            contentDescription =
                                stringResource(R.string.download_image_content_description),
                            modifier =
                                Modifier.size(UiConfigs.ChatPage.PhotoAlbum.Preview.ButtonIconSize),
                            tint = Color.White,
                        )
                        Text(
                            text = stringResource(R.string.download_button),
                            color = Color.White,
                            fontSize = UiConfigs.ChatPage.PhotoAlbum.Preview.ButtonTextFontSize,
                            fontWeight = FontWeight.Medium,
                        )
                    }
                }

                if (onReport != null) {
                    ReportButton(
                        onClick = { onReport() },
                        iconSize = UiConfigs.ChatPage.PhotoAlbum.Preview.ButtonIconSize,
                        textFontSize = 14.sp,
                    )
                }
            }
        }

        if (showUpscaleCreditsDialog) {
            AlertDialog(
                onDismissRequest = {
                    if (!isDeductingUpscaleCredits) {
                        showUpscaleCreditsDialog = false
                    }
                },
                title = {
                    Text(
                        text = stringResource(R.string.image_upscale_locked_title),
                        color = Color.White,
                    )
                },
                text = {
                    Text(
                        text =
                            stringResource(
                                R.string.image_upscale_locked_message,
                                UiConfigs.Credits.VipImageUpscaleCost,
                            ),
                        color = Color.White.copy(alpha = 0.85f),
                    )
                },
                confirmButton = {
                    TextButton(
                        enabled = !isDeductingUpscaleCredits,
                        onClick = {
                            if (isDeductingUpscaleCredits) return@TextButton
                            isDeductingUpscaleCredits = true
                            scope.launch {
                                val cost = UiConfigs.Credits.VipImageUpscaleCost
                                val availableCredits = BoostManager.boostState.value.availablePoints
                                trackUpscaleEvent(
                                    "unlock_attempt",
                                    "required_credits" to cost,
                                    "available_credits" to availableCredits,
                                )
                                if (availableCredits < cost) {
                                    trackUpscaleEvent(
                                        "unlock_failed_not_enough_credits",
                                        "required_credits" to cost,
                                        "available_credits" to availableCredits,
                                    )
                                    isDeductingUpscaleCredits = false
                                    ToastUtils.showShort(R.string.credits_not_enough)
                                    return@launch
                                }

                                val deducted =
                                    try {
                                        BoostManager.deductPoints(cost)
                                    } catch (_: BoostException) {
                                        false
                                    }

                                isDeductingUpscaleCredits = false
                                if (deducted) {
                                    hasTemporaryUpscaleAccess = true
                                    trackUpscaleEvent(
                                        "unlock_success_credits",
                                        "required_credits" to cost,
                                        "available_credits" to availableCredits,
                                    )
                                    showUpscaleCreditsDialog = false
                                    showUpscaleOptionsDialog = true
                                    ToastUtils.showShort(R.string.credits_deducted, cost)
                                } else {
                                    trackUpscaleEvent(
                                        "unlock_failed_deduct_error",
                                        "required_credits" to cost,
                                        "available_credits" to availableCredits,
                                    )
                                    ToastUtils.showShort(R.string.credits_not_enough)
                                }
                            }
                        },
                    ) {
                        Text(
                            text =
                                if (isDeductingUpscaleCredits) {
                                    stringResource(R.string.image_upscale_unlocking)
                                } else {
                                    stringResource(R.string.image_upscale_use_credits)
                                },
                            color = Color.White,
                        )
                    }
                },
                dismissButton = {
                    TextButton(
                        enabled = !isDeductingUpscaleCredits,
                        onClick = { showUpscaleCreditsDialog = false },
                    ) {
                        Text(text = stringResource(R.string.cancel), color = Color.White)
                    }
                },
                containerColor = Color(0xFF1E1E1E),
            )
        }

        if (showUpscaleOptionsDialog) {
            AlertDialog(
                onDismissRequest = { showUpscaleOptionsDialog = false },
                title = {
                    Text(
                        text = stringResource(R.string.image_upscale_dialog_title),
                        color = Color.White,
                    )
                },
                text = {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(UiConfigs.Spacing.Small),
                    ) {
                        IMAGE_UPSCALE_FACTORS.forEach { factor ->
                            val isSelected = factor == selectedUpscaleFactor
                            TextButton(
                                modifier = Modifier.fillMaxWidth(),
                                onClick = {
                                    val previousFactor = selectedUpscaleFactor
                                    selectedUpscaleFactor = factor
                                    showUpscaleOptionsDialog = false
                                    trackUpscaleEvent(
                                        "apply_factor",
                                        "previous_factor" to previousFactor,
                                        "target_factor" to factor,
                                    )
                                    ToastUtils.showShort(R.string.image_upscale_applied, factor)
                                },
                            ) {
                                Text(
                                    text = stringResource(R.string.image_upscale_option, factor),
                                    color = Color.White,
                                    fontWeight =
                                        if (isSelected) FontWeight.SemiBold else FontWeight.Normal,
                                )
                            }
                        }
                    }
                },
                confirmButton = {},
                dismissButton = {
                    TextButton(onClick = { showUpscaleOptionsDialog = false }) {
                        Text(text = stringResource(R.string.cancel), color = Color.White)
                    }
                },
                containerColor = Color(0xFF1E1E1E),
            )
        }

        // 右下角操作按钮（如果提供）
        if (onAction != null && actionLabel != null) {
            TextButton(
                onClick = { onAction() },
                modifier =
                    Modifier.align(Alignment.BottomEnd)
                        .padding(16.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color.Black.copy(alpha = 0.7f), RoundedCornerShape(8.dp)),
            ) {
                Text(
                    text = actionLabel,
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Medium,
                )
            }
        }
    }
}
