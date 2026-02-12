package com.ai.intellimate.xb.navigation

import androidx.compose.runtime.LaunchedEffect
import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavType
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.ai.intellimate.chat.ChatScreen
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.xb.helper.AgentStore

fun NavGraphBuilder.chatGraph(navController: NavController, chatViewModel: ChatViewModel) {

    // 定义聊天页面路由
    // 深度链接的参数需要指明类型，否则可能会出现类型转换错误
    composable(
        route = Routes.Chat.ChatPage,
        arguments =
            listOf(
                navArgument("agentId") { type = NavType.StringType },
                navArgument("showBoost") { type = NavType.BoolType },
                navArgument("shouldAutoFocusInput") { type = NavType.BoolType },
                navArgument("isDeleted") {
                    type = NavType.BoolType
                    defaultValue = false
                },
                navArgument("fromPage") {
                    type = NavType.StringType
                    defaultValue = null
                    nullable = true
                },
            ),
    ) { backStackEntry ->
        val agentId = backStackEntry.arguments?.getString("agentId")
        val showBoost = backStackEntry.arguments?.getBoolean("showBoost")
        val shouldAutoFocusInput = backStackEntry.arguments?.getBoolean("shouldAutoFocusInput")
        val isDeleted = backStackEntry.arguments?.getBoolean("isDeleted") ?: false
        val refreshCount =
            backStackEntry.savedStateHandle.get<Int>(RoutesChat.VoiceCallResultKeys.MESSAGE_COUNT)
                ?: backStackEntry.savedStateHandle.get<Int>(
                    RoutesChat.VoiceCallResultKeys.LEGACY_MESSAGE_COUNT
                )
                ?: 1
        val refreshVoiceSessionId =
            backStackEntry.savedStateHandle.get<String>(RoutesChat.VoiceCallResultKeys.SESSION_ID)
        val voiceCallRecordingPath =
            backStackEntry.savedStateHandle.get<String>(
                RoutesChat.VoiceCallResultKeys.RECORDING_PATH
            )
        val voiceCallRecordingDurationMs =
            backStackEntry.savedStateHandle.get<Long>(
                RoutesChat.VoiceCallResultKeys.RECORDING_DURATION_MS
            )
        val voiceCallTurnRecordingsJson =
            backStackEntry.savedStateHandle.get<String>(
                RoutesChat.VoiceCallResultKeys.TURN_RECORDINGS_JSON
            )

        LaunchedEffect(
            agentId,
            refreshCount,
            refreshVoiceSessionId,
            voiceCallRecordingPath,
            voiceCallRecordingDurationMs,
            voiceCallTurnRecordingsJson,
        ) {
            val agent = AgentStore.getAgent(agentId = agentId)
            if (agentId != null) {
                if (agent != null) {
                    if (isDeleted) agent.isDeleted = true
                    chatViewModel.setAgentInfo(agent)
                } else {
                    chatViewModel.clearAllData()
                    chatViewModel.setAgentID(agentId)
                }
            }

            backStackEntry.savedStateHandle.remove<Int>(RoutesChat.VoiceCallResultKeys.MESSAGE_COUNT)
            backStackEntry.savedStateHandle.remove<Int>(
                RoutesChat.VoiceCallResultKeys.LEGACY_MESSAGE_COUNT
            )
            backStackEntry.savedStateHandle.remove<String>(
                RoutesChat.VoiceCallResultKeys.SESSION_ID
            )
            backStackEntry.savedStateHandle.remove<String>(
                RoutesChat.VoiceCallResultKeys.RECORDING_PATH
            )
            backStackEntry.savedStateHandle.remove<Long>(
                RoutesChat.VoiceCallResultKeys.RECORDING_DURATION_MS
            )
            backStackEntry.savedStateHandle.remove<String>(
                RoutesChat.VoiceCallResultKeys.TURN_RECORDINGS_JSON
            )
        }

        ChatScreen(
            navController,
            chatViewModel = chatViewModel,
            showBackButton = true,
            shouldShowBoostSheetOnOpen = showBoost == true,
            shouldAutoFocusInput = shouldAutoFocusInput ?: true,
            onCall = { agentId?.let { navController.navigate(Routes.Chat.voiceCall(it)) } },
            fromPage = backStackEntry.arguments?.getString("fromPage"),
            refreshMessageCount = refreshCount,
            refreshVoiceSessionId = refreshVoiceSessionId,
            voiceCallRecordingPath = voiceCallRecordingPath,
            voiceCallRecordingDurationMs = voiceCallRecordingDurationMs ?: 0L,
            voiceCallTurnRecordingsJson = voiceCallTurnRecordingsJson,
        )
    }
}
