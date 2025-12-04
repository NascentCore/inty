package com.ai.intellimate.xb.navigation

import androidx.compose.runtime.Composable
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.ai.intellimate.HomeScreen
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.SplashLoginUI
import com.ai.intellimate.chat.ChatScreen
import com.ai.intellimate.profile.ModifyProfileScreen
import com.ai.intellimate.settings.SettingScreen
import com.ai.intellimate.vip.VipCenterContent

@Composable
fun AppNavHost(page: String, viewModel: MainViewModel, factory: ViewModelProvider.Factory) {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = page,
    ) {
        composable(Routes.SplashLogin) {
            SplashLoginUI(navController = navController, mainViewModel = viewModel)
        }
        composable(Routes.HomeTab) {
            HomeScreen(
                navController = navController,
                mainViewModel = viewModel,
                viewModelFactory = factory,
            )
        }

        composable(Routes.VipCenter) {
            VipCenterContent(navController = navController)
        }
        composable(Routes.Settings) {
            SettingScreen(navController)
        }
        composable(Routes.ChatPage) { backStackEntry ->
            val agentId = backStackEntry.arguments?.getString("agentId");
            ChatScreen(
                navController,
                chatViewModel = viewModel(),
                showBackButton = true,
                agentId = agentId
            )
        }
        composable(Routes.ModifyProfile) {
            ModifyProfileScreen(
                navController,
            )
        }
    }
}