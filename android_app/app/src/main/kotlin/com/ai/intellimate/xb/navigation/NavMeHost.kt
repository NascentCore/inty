package com.ai.intellimate.xb.navigation

import androidx.compose.runtime.remember
import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavType
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.agent.report.ReportPage
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.profile.ModifyProfileScreen
import com.ai.intellimate.profile.uploadSelfieScreen
import com.ai.intellimate.settings.SettingScreen
import com.ai.intellimate.settings.check.CheckInScreen
import com.ai.intellimate.vip.SubsManagementScreen
import com.ai.intellimate.vip.VipCenterContent
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling

fun NavGraphBuilder.meGraph(
    navController: NavController,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
) {
    // 定义vip订阅页面路由
    composable(
        route = Routes.Me.VipCenter,
        arguments =
            listOf(
                navArgument("pageSource") {
                    type = NavType.StringType
                    nullable = true
                }
            ),
    ) { backStackEntry ->
        VipCenterContent(
            navController,
            pageFrom = backStackEntry.arguments?.getString("pageSource"),
        )
    }

    composable(Routes.Me.CheckIn) { IgnoreSystemFontScaling { CheckInScreen(navController) } }

    // 定义设置页面路由
    composable(Routes.Me.Settings) {
        SettingScreen(navController, mainViewModel = mainViewModel, chatViewModel = chatViewModel)
    }

    // 定义编辑资料页面路由
    composable(Routes.Me.ModifyProfile) { ModifyProfileScreen(navController) }

    composable(Routes.Me.SubsManagement) { SubsManagementScreen(navController) }

    // 定义举报相关页面
    composable(
        route = Routes.Me.ReportPage,
        arguments =
            listOf(
                navArgument("isFeedback") { type = NavType.BoolType },
                navArgument("targetType") { type = NavType.StringType },
                navArgument("targetId") { type = NavType.StringType },
            ),
    ) { backStackEntry ->
        val isFeedback = backStackEntry.arguments?.getBoolean("isFeedback")
        val targetType = backStackEntry.arguments?.getString("targetType")
        val targetId = backStackEntry.arguments?.getString("targetId")
        val initialEvidenceImageUrl =
            remember(backStackEntry) {
                navController.previousBackStackEntry
                    ?.savedStateHandle
                    ?.remove<String>(Routes.Me.ReportInitialEvidenceImageUrlKey)
                    .orEmpty()
            }
        ReportPage(
            navController = navController,
            isFeedbackModel = isFeedback ?: false,
            targetType = targetType ?: "USER",
            targetId = targetId ?: "",
            initialEvidenceImageUrl = initialEvidenceImageUrl,
        )
    }

    uploadSelfieScreen(onBack = { navController.navigateUp() })
}
