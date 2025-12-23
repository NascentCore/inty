package com.ai.intellimate.xb.navigation

import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.compose.composable
import com.ai.intellimate.agent.generate.CreateRoleScreen
import com.ai.intellimate.vip.VipCenterContent

fun NavGraphBuilder.createGraph(navController: NavController) {
    // 定义vip订阅页面路由
    composable(Routes.Creat.CreateRole) {
//        VipCenterContent(navController)
        CreateRoleScreen(
            navController,
        )
    }
}