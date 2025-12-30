package com.ai.intellimate.xb.navigation

import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.ai.intellimate.HomeScreen
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.SplashLoginUI
import com.ai.intellimate.agent.info.AgentInfoViewModel
import com.ai.intellimate.call.VoiceCallScreen
import com.ai.intellimate.chat.viewmodel.ChatViewModel

/**
 * 应用导航宿主组件
 *
 * 这是应用的根导航容器，负责管理应用内所有主要页面的导航和转场动画。 使用 Jetpack Compose Navigation 实现页面间的路由和跳转。
 *
 * 设计决策：
 * - navController 参数为必需参数，由调用方传入
 * - 原因：MainActivity 需要在庆祝弹窗点击后导航到随机圣诞角色，需要访问 NavController
 * - 调用方负责创建和管理 NavController 的生命周期
 *
 * @param page 初始页面路由，决定应用启动时显示的第一个页面（如登录页或主页）
 * @param mainViewModel 主视图模型，用于管理应用级别的状态和数据
 * @param chatViewModel 聊天视图模型，用于管理聊天相关的状态
 * @param factory ViewModel 工厂，用于创建和管理 ViewModel 实例
 * @param navController 导航控制器，由调用方创建并传入
 */
@Composable
fun AppNavHost(
    page: String,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    factory: ViewModelProvider.Factory,
    navController: NavHostController,
) {

    val pushAgentId by mainViewModel.pushAgentId.collectAsState()
    LaunchedEffect(pushAgentId) {
        if (pushAgentId.isEmpty()) return@LaunchedEffect
        mainViewModel.updatePushAgentId("")
        navController.navigate(Routes.Chat.chatPage(pushAgentId, false))
    }
    val agentInfoViewModel: AgentInfoViewModel = viewModel()

    // 配置导航宿主，定义所有可导航的页面和转场动画
    NavHost(
        navController = navController,
        // 设置启动时的初始页面，根据登录状态动态决定（登录页或主页）
        startDestination = page,
        // 进入新页面时的转场动画：从右侧滑入 + 淡入效果，持续 400ms
        enterTransition = {
            slideIntoContainer(
                towards = AnimatedContentTransitionScope.SlideDirection.Start,
                animationSpec = tween(400),
            ) + fadeIn(animationSpec = tween(400))
        },
        // 返回上一页时的转场动画：从左侧滑入 + 淡入效果，持续 400ms
        popEnterTransition = {
            slideIntoContainer(
                towards = AnimatedContentTransitionScope.SlideDirection.End,
                animationSpec = tween(400),
            ) + fadeIn(animationSpec = tween(400))
        },
    ) {
        // 定义登录/启动页面路由
        composable(Routes.SplashLogin) {
            SplashLoginUI(navController = navController, mainViewModel = mainViewModel)
        }

        // 定义主页标签页路由（包含 Explore、Messages、Me 等底部导航）
        composable(Routes.HomeTab) {
            HomeScreen(
                navController = navController,
                mainViewModel = mainViewModel,
                viewModelFactory = factory,
            )
        }

        // 定义语音通话页面路由
        composable(
            route = Routes.Chat.VoiceCall,
            arguments = listOf(navArgument("agentId") { type = NavType.StringType }),
        ) { backStackEntry ->
            val agentId = backStackEntry.arguments?.getString("agentId")

            if (agentId != null) {
                VoiceCallScreen(
                    onBack = { navController.popBackStack() },
                    onVip = { navController.navigate(Routes.Me.VipCenter)},
                    onVipMoreInfo = { navController.navigate(Routes.Me.VipCenter) },
                    agentId = agentId
                )
            }
        }

        homeGraph(navController, agentInfoViewModel)
        chatGraph(navController, chatViewModel)
        createGraph(navController)
        exploreGraph(navController)
        meGraph(navController, mainViewModel, chatViewModel)
    }
}
