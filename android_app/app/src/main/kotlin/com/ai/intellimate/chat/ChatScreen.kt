package com.ai.intellimate.chat

import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.theme.HeartColor
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavController
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.FeedbackRequestDialog
import com.ai.intellimate.ui.components.AgentBackground
import com.ai.intellimate.xb.navigation.Routes

/**
 * 聊天页面组件（通过导航系统显示）
 *
 * 使用场景：
 * 1. 从 MainActivity 的导航系统进入 - 通过 Routes.ChatPage 路由，在 AppNavHost 中定义
 * 2. 从消息列表 Tab 点击会话项 - HomeScreen.MessagesTabContent 中调用
 *    navController.navigate(Routes.Chat.chatPage(...))
 * 3. 从消息列表 Tab 点击收藏的角色 - HomeScreen.MessagesTabContent 中调用
 *    navController.navigate(Routes.Chat.chatPage(...))
 * 4. 从探索 Tab 点击角色 - HomeScreen.ExploreTabContent 中调用
 *    navController.navigate(Routes.Chat.chatPage(...))
 * 5. 从个人中心 Tab 点击角色 - HomeScreen.ProfileTabContent 中调用
 *    navController.navigate(Routes.Chat.chatPage(...))
 * 6. 从其他通过导航系统跳转的地方 - 任何使用 navController.navigate(Routes.Chat.chatPage(...)) 的地方
 *
 * 注意：此组件在 MainActivity 的 NavHost 中显示，不是独立的 Activity。 只有推送通知和 Boost 排行榜场景使用独立的 ChatActivity。
 */
@Composable
internal fun ChatScreen(
    navController: NavController,
    chatViewModel: ChatViewModel,
    showBackButton: Boolean = false,
    shouldAutoFocusInput: Boolean = true,
    onCall: () -> Unit = {},
    shouldShowBoostSheetOnOpen: Boolean = false,
    fromPage: String? = null,
    refreshMessageCount: Int = 0,
) {
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val showFeedbackDialog by chatViewModel.showFeedbackRequestDialog.collectAsState()
    val showImageFeedbackDialog by chatViewModel.showImageFeedbackRequestDialog.collectAsState()
    val imageFeedbackPayload by chatViewModel.imageFeedbackNavigationPayload.collectAsState()
    val autoPlayAnimation by SettingStateManager.autoPlayAnimationFlow.collectAsState()

    Box(modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor)) {
        // 背景图放在最底层，不受 imePadding 影响
        AgentBackground(
            agentInfo = agentInfo,
            showGradients = true,
            isLoading = false,
            isCurrentPage = true,
            enableAnimatedBackground = autoPlayAnimation,
            modifier = Modifier.fillMaxSize(),
        )

        ChatPage(
            navController,
            modifier = Modifier.fillMaxSize().imePadding().navigationBarsPadding(),
            chatViewModel = chatViewModel,
            showBackButton = showBackButton,
            shouldShowBoostSheetOnOpen = shouldShowBoostSheetOnOpen,
            shouldAutoFocusInput = shouldAutoFocusInput,
            onCall = onCall,
            fromPage = fromPage,
            refreshMessageCount = refreshMessageCount,
        )

        if (showImageFeedbackDialog) {
            FeedbackRequestDialog(
                onCancel = { chatViewModel.hideImageFeedbackRequestDialog() },
                onSendSuggestions = {
                    val payload = imageFeedbackPayload
                    if (payload != null) {
                        navController.currentBackStackEntry
                            ?.savedStateHandle
                            ?.set(
                                Routes.Me.ReportInitialEvidenceImageUrlKey,
                                payload.imageUrl,
                            )
                        navController.currentBackStackEntry
                            ?.savedStateHandle
                            ?.set(
                                Routes.Me.ReportImageFeedbackVoteKey,
                                payload.vote,
                            )
                        navController.navigate(
                            Routes.Me.reportPage(
                                isFeedback = true,
                                targetType = "USER",
                                targetId = payload.targetId,
                            )
                        )
                    }
                    chatViewModel.hideImageFeedbackRequestDialog()
                },
            )
        } else if (showFeedbackDialog) {
            // 通用反馈请求对话框
            FeedbackRequestDialog(
                onCancel = { chatViewModel.hideFeedbackRequestDialog() },
                onSendSuggestions = {
                    chatViewModel.hideFeedbackRequestDialog()
                    navController.navigate(
                        Routes.Me.reportPage(
                            isFeedback = true,
                            targetType = "AGENT",
                            targetId = agentInfo?.id ?: "",
                        )
                    )
                    //                    ReportActivity.launchFeedback(context)
                },
            )
        }
    }
}
