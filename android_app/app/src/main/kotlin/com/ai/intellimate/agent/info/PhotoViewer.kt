package com.ai.intellimate.agent.info

import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.navigation.NavController
import com.ai.intellimate.R
import com.ai.intellimate.chat.ui.FullScreenImageViewer
import com.ai.intellimate.utils.ChatBackgroundUtils
import com.ai.intellimate.xb.navigation.Routes

/**
 * 角色相册图片全屏预览对话框
 *
 * 这是一个可复用的组件，封装了角色相册图片的全屏预览功能。 支持设置图片为聊天背景，并统一处理 Dialog 和 FullScreenImageViewer 的逻辑。
 *
 * @param previewImageUrl 要预览的图片 URL，如果为 null 则不显示对话框
 * @param agentId 角色 ID，用于设置聊天背景
 * @param onDismiss 关闭对话框的回调
 * @param onBackgroundChanged 可选的背景变化回调，当设置背景后会被调用并传入新的背景 URL
 */
@Composable
fun AgentGalleryImagePreviewDialog(
    navController: NavController,
    previewImageUrl: String?,
    agentId: String,
    onDismiss: () -> Unit,
    onBackgroundChanged: ((String?) -> Unit)? = null,
) {
    if (previewImageUrl != null) {
        Dialog(
            onDismissRequest = onDismiss,
            properties =
                DialogProperties(
                    usePlatformDefaultWidth = false,
                    dismissOnClickOutside = true,
                    dismissOnBackPress = true,
                ),
        ) {
            val currentImageUrl = previewImageUrl
            FullScreenImageViewer(
                imageUrl = currentImageUrl,
                onDismiss = onDismiss,
                onAction = {
                    if (agentId.isNotBlank() && currentImageUrl.isNotBlank()) {
                        val newBackgroundUrl =
                            ChatBackgroundUtils.setChatBackground(agentId, currentImageUrl)
                        onBackgroundChanged?.invoke(newBackgroundUrl)
                        onDismiss()
                    }
                },
                actionLabel = stringResource(R.string.agent_gallery_set_as_background),
                onReport = {
                    if (agentId.isNotBlank()) {
                        navController.currentBackStackEntry
                            ?.savedStateHandle
                            ?.set(Routes.Me.ReportInitialEvidenceImageUrlKey, currentImageUrl)
                        navController.navigate(Routes.Me.reportPage(false, "AGENT", agentId))
                        //                        ReportActivity.launch(context, targetType =
                        // "AGENT", targetId = agentId)
                    }
                },
            )
        }
    }
}
