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
            ),
    ) { backStackEntry ->
        val agentId = backStackEntry.arguments?.getString("agentId")
        val showBoost = backStackEntry.arguments?.getBoolean("showBoost")
        val shouldAutoFocusInput = backStackEntry.arguments?.getBoolean("shouldAutoFocusInput")
        val isDeleted = backStackEntry.arguments?.getBoolean("isDeleted") ?: false
        LaunchedEffect(agentId) {
            val agent = AgentStore.getAgent(agentId = agentId)
            if (agentId != null) {
                if (agent != null) {
                    if (isDeleted) agent.isDeleted = true
                    chatViewModel.setAgentInfo(agent, true)
                } else {
                    chatViewModel.clearAllData()
                    chatViewModel.setAgentID(agentId)
                }
                chatViewModel.updateUserInfo()
            }
        }

        ChatScreen(
            navController,
            chatViewModel = chatViewModel,
            showBackButton = true,
            shouldShowBoostSheetOnOpen = showBoost == true,
            shouldAutoFocusInput = shouldAutoFocusInput ?: true,
            onCall = { agentId?.let { navController.navigate(Routes.Chat.voiceCall(it)) } },
        )
    }
}
