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
    composable(Routes.Creat.CreateRole) {
        CreateRoleScreen(
            navController,
            agentInfo = AgentStore.agentInfoDraft
        )
    }

    // 定义生成头像路由
    composable(
        route = Routes.Creat.AvatarGenerate,
        arguments =
            listOf(
                navArgument("initialPrompt") { type = NavType.StringType },
            ),
    ) { backStackEntry ->
        val initialPrompt = backStackEntry.arguments?.getString("initialPrompt")
        AvatarGeneratePage(
            navController,
            initialPrompt = initialPrompt,
        )
    }
}