package com.ai.intellimate.chat

import ai.sxwl.android.data.billing.BillingRepository
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
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavController
import com.ai.intellimate.BuildConfig
import com.ai.intellimate.R
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.FeedbackRequestDialog
import com.ai.intellimate.ui.UnlimitChatDialog
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
    fromPage: String? = null
) {
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val chatMessages by chatViewModel.msgs.collectAsState()
    val showFeedbackDialog by chatViewModel.showFeedbackRequestDialog.collectAsState()
    val autoPlayAnimation by SettingStateManager.autoPlayAnimationFlow.collectAsState()
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
    val context = LocalContext.current
    val hasLoadingMessage =
        chatMessages.any { msg ->
            val hasGeneratedImage = msg.hasGeneratedImage()
            val generatedImageUrl = msg.getGeneratedImageUrl()
            msg.content == "loading_animation" &&
                !hasGeneratedImage &&
                generatedImageUrl != "loading"
        }

    fun isVipTag(tag: String?): Boolean {
        val normalized =
            tag?.trim()?.removePrefix("#")?.lowercase()?.takeIf { it.isNotBlank() } ?: return false
        return normalized == "vip"
    }

    val isVipCharacter =
        remember(agentInfo?.id, agentInfo?.tags) { agentInfo?.tags?.any { isVipTag(it) } == true }

    val showVipCharacterLockedDialog = isVipCharacter && !vipStatus.isSubscribed

    Box(modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor)) {
        // 背景图放在最底层，不受 imePadding 影响
        AgentBackground(
            agentInfo = agentInfo,
            showGradients = true,
            isLoading = hasLoadingMessage,
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
            fromPage = fromPage
        )

        // VIP 角色聊天权限拦截：非订阅用户不允许进入 VIP 角色聊天
        if (showVipCharacterLockedDialog && BuildConfig.BUILD_TYPE == "release") {
            val dialogData =
                ChatDialogData(
                    R.drawable.img_unlimit_dialog_bg,
                    stringResource(R.string.vip_character_chat_locked_content),
                    stringResource(R.string.vip_character_chat_locked_cta),
                )
            UnlimitChatDialog(
                dialogData = dialogData,
                onCancel = { navController.popBackStack() },
                onSure = { navController.navigate(Routes.Me.VipCenter) },
                onMoreInfo = { navController.navigate(Routes.Me.VipCenter) },
            )
        }

        // 反馈请求对话框
        if (showFeedbackDialog) {
            FeedbackRequestDialog(
                onCancel = { chatViewModel.hideFeedbackRequestDialog() },
                onSendSuggestions = {
                    chatViewModel.hideFeedbackRequestDialog()
                    navController.navigate(Routes.Me.reportPage(true))
                    //                    ReportActivity.launchFeedback(context)
                },
            )
        }
    }
}
