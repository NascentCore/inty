package com.ai.intellimate.xb.navigation

import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.runtime.Composable
import androidx.lifecycle.ViewModelProvider
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.ai.intellimate.HomeScreen
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.SplashLoginUI
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.settings.SettingScreen

@Composable
fun AppNavHost(page: String, mainViewModel: MainViewModel, chatViewModel: ChatViewModel, factory: ViewModelProvider.Factory) {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = page,
        enterTransition = {
            slideIntoContainer(
                towards = AnimatedContentTransitionScope.SlideDirection.Start,
                animationSpec = tween(400)
            ) + fadeIn(animationSpec = tween(400))
        },
        popEnterTransition = {
            slideIntoContainer(
                towards = AnimatedContentTransitionScope.SlideDirection.End,
                animationSpec = tween(400)
            ) + fadeIn(animationSpec = tween(400))
        },
    ) {
        composable(Routes.SplashLogin) {
            SplashLoginUI(navController = navController, mainViewModel = mainViewModel)
        }
        composable(Routes.HomeTab) {
            HomeScreen(
                navController = navController,
                mainViewModel = mainViewModel,
                viewModelFactory = factory,
            )
        }

        composable(Routes.Settings) {
            SettingScreen(
                navController,
                mainViewModel = mainViewModel,
                chatViewModel = chatViewModel
            )
        }

    }
}