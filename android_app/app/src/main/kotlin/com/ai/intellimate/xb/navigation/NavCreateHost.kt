package com.ai.intellimate.xb.navigation

import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavType
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.ai.intellimate.agent.generate.AvatarGeneratePage
import com.ai.intellimate.agent.generate.CreateRoleScreen
import com.ai.intellimate.xb.helper.AgentStore

fun NavGraphBuilder.createGraph(navController: NavController) {
    // 定义创建角色路由
    composable(
        route = Routes.Creat.CreateRole,
        arguments =
            listOf(
                navArgument("draftId") { type = NavType.StringType },
                navArgument("agentId") {
                    type = NavType.StringType
                    defaultValue = ""
                },
            ),
    ) { backStackEntry ->
        val draftId = backStackEntry.arguments?.getString("draftId")
        val agentId = backStackEntry.arguments?.getString("agentId").orEmpty()
        val agentInfo = agentId.takeIf { it.isNotBlank() }?.let(AgentStore::getAgent)
        CreateRoleScreen(navController, agentInfo = agentInfo, draftId = draftId)
    }

    // 定义生成头像路由
    composable(
        route = Routes.Creat.AvatarGenerate,
        arguments = listOf(navArgument("initialPrompt") { type = NavType.StringType }),
    ) { backStackEntry ->
        val initialPrompt = backStackEntry.arguments?.getString("initialPrompt")
        AvatarGeneratePage(navController, initialPrompt = initialPrompt)
    }
}
