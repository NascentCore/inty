package com.ai.intellimate.chat

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
import com.ai.intellimate.ui.components.AgentBackground

@Composable
internal fun ChatScreen(
    navController: NavController,
    chatViewModel: ChatViewModel,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
    isCurrentPage: Boolean = true,
    shouldAutoFocusInput: Boolean = true,
    onInputFocusChange: (Boolean) -> Unit = {},
    onKeyboardVisible: (Boolean) -> Unit = {},
    pageSourceOverride: String? = null, // 如果提供，则使用此 pageSource（通常来自 ChatActivity）
    isGuideVisible: Boolean = false,
    shouldShowBoostSheetOnOpen: Boolean = false,
    agentId: String? = null
) {
    val agentInfo by chatViewModel.agentInfo.collectAsState()
    val chatMessages by chatViewModel.msgs.collectAsState()
    val hasLoadingMessage =
        chatMessages.any { msg ->
            val hasGeneratedImage = msg.hasGeneratedImage()
            val generatedImageUrl = msg.getGeneratedImageUrl()
            msg.content == "loading_animation" &&
                    !hasGeneratedImage &&
                    generatedImageUrl != "loading"
        }

    Box(modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor)) {
        // 背景图放在最底层，不受 imePadding 影响
        AgentBackground(
            agentInfo = agentInfo,
            showGradients = true,
            isLoading = hasLoadingMessage,
            isCurrentPage = true,
            modifier = Modifier.fillMaxSize(),
        )

        ChatPage(
            navController,
            modifier = Modifier.fillMaxSize().imePadding().navigationBarsPadding(),
            chatViewModel = chatViewModel,
            showBackButton = true,
            onBack = { navController.popBackStack() },
            shouldShowBoostSheetOnOpen = shouldShowBoostSheetOnOpen,
        )
    }
}