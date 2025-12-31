package com.ai.intellimate.xb.navigation

import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.compose.composable
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.profile.ModifyProfileScreen
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
    composable(Routes.Me.VipCenter) { VipCenterContent(navController) }

    composable(Routes.Me.CheckIn) { IgnoreSystemFontScaling { CheckInScreen(navController) } }

    // 定义设置页面路由
    composable(Routes.Me.Settings) {
        SettingScreen(navController, mainViewModel = mainViewModel, chatViewModel = chatViewModel)
    }

    // 定义编辑资料页面路由
    composable(Routes.Me.ModifyProfile) {
        ModifyProfileScreen(navController)
    }

    composable(Routes.Me.SubsManagement) {
        SubsManagementScreen( navController)
    }
}
