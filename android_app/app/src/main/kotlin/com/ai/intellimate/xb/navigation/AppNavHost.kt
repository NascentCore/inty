package com.ai.intellimate.xb.navigation

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.animation.AnimatedContentTransitionScope
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.foundation.layout.Box
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.ai.intellimate.HomeScreen
import com.ai.intellimate.MainViewModel
import com.ai.intellimate.SplashLoginUI
import com.ai.intellimate.agent.info.AgentInfoViewModel
import com.ai.intellimate.agent.info.AiAgentInfoScreen
import com.ai.intellimate.agent.info.PhotoAlbumScreen
import com.ai.intellimate.boost.BoostLeaderboardScreen
import com.ai.intellimate.chat.ChatScreen
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.explore.special.CollectionDetailVM
import com.ai.intellimate.explore.special.ThemedDetailScreen
import com.ai.intellimate.settings.SettingScreen
import com.ai.intellimate.settings.check.CheckInScreen
import com.ai.intellimate.vip.VipCenterContent
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling
import com.ai.intellimate.xb.helper.AgentStore
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.net.URLDecoder

/**
 * 应用导航宿主组件
 *
 * 这是应用的根导航容器，负责管理应用内所有主要页面的导航和转场动画。 使用 Jetpack Compose Navigation 实现页面间的路由和跳转。
 *
 * @param page 初始页面路由，决定应用启动时显示的第一个页面（如登录页或主页）
 * @param mainViewModel 主视图模型，用于管理应用级别的状态和数据
 * @param chatViewModel 聊天视图模型，用于管理聊天相关的状态
 * @param factory ViewModel 工厂，用于创建和管理 ViewModel 实例
 */
@Composable
fun AppNavHost(
    page: String,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
    factory: ViewModelProvider.Factory,
) {
    // 创建并记住导航控制器，用于管理页面导航栈
    val navController = rememberNavController()

    val pushAgentId by mainViewModel.pushAgentId.collectAsState()
    LaunchedEffect(pushAgentId) {
        if (pushAgentId.isEmpty()) return@LaunchedEffect
        mainViewModel.updatePushAgentId("")
        navController.navigate(Routes.chatPage(pushAgentId, false))
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

        // 定义设置页面路由
        composable(Routes.Settings) {
            SettingScreen(
                navController,
                mainViewModel = mainViewModel,
                chatViewModel = chatViewModel,
            )
        }

        // 定义vip订阅页面路由
        composable(Routes.VipCenter) { VipCenterContent(navController) }

        // 定义聊天页面路由
        // 深度链接的参数需要指明类型，否则可能会出现类型转换错误
        composable(
            route = Routes.ChatPage,
            arguments =
                listOf(
                    navArgument("agentId") { type = NavType.StringType },
                    navArgument("showBoost") { type = NavType.BoolType },
                    navArgument("shouldAutoFocusInput") { type = NavType.BoolType },
                ),
        ) { backStackEntry ->
            val agentId = backStackEntry.arguments?.getString("agentId")
            val showBoost = backStackEntry.arguments?.getBoolean("showBoost")
            val shouldAutoFocusInput = backStackEntry.arguments?.getBoolean("shouldAutoFocusInput")
            LaunchedEffect(agentId) {
                val agent = AgentStore.getAgent(agentId = agentId)
                if (agentId != null) {
                    if (agent != null) {
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
                agentId = agentId,
            )
        }

        composable(Routes.BoostLeaderboard) { BoostLeaderboardScreen(navController) }
        composable(Routes.CheckIn) { IgnoreSystemFontScaling { CheckInScreen(navController) } }

        composable(Routes.AgentInfoPage) { backStackEntry ->
            val agentId = backStackEntry.arguments?.getString("agentId")
            val agentInfo = AgentStore.getAgent(agentId = agentId)
            LaunchedEffect(agentId) {
                if (agentInfo != null) {
                    agentInfoViewModel.setAgentInfo(agentInfo)
                } else {
                    agentInfoViewModel.setAgentID(agentId!!)
                }
            }

            if (agentInfo != null) {
                val galleryImages = agentInfoViewModel.chatImageGallery.collectAsState()
                AiAgentInfoScreen(
                    agent = agentInfo,
                    galleryItems = galleryImages.value,
                    navController = navController,
                )
            } else {
                Box {}
            }
        }

        composable(Routes.AgentPhotoAlbum) { backStackEntry ->
            val agentId = backStackEntry.arguments?.getString("agentId")
            val agentInfo = AgentStore.getAgent(agentId = agentId)
            LaunchedEffect(agentId) {
                if (agentInfo != null) {
                    agentInfoViewModel.setAgentInfo(agentInfo)
                } else {
                    agentInfoViewModel.setAgentID(agentId!!)
                }
            }

            if (agentInfo != null) {
                val galleryImages = agentInfoViewModel.chatImageGallery.collectAsState()
                PhotoAlbumScreen(
                    agent = agentInfo,
                    galleryItems = galleryImages.value,
                    onBack = { navController.popBackStack() },
                )
            } else {
                Box {}
            }
        }

        // 定义角色专区详情页面路由
        composable(Routes.CollectionDetail) { backStackEntry ->
            val themeId = backStackEntry.arguments?.getString("themeId") ?: ""
            val themeTitleEncoded = backStackEntry.arguments?.getString("themeTitle") ?: ""
            val themeDescriptionEncoded =
                backStackEntry.arguments?.getString("themeDescription") ?: ""
            val isChristmasString = backStackEntry.arguments?.getString("isChristmas") ?: "false"
            val isChristmas = isChristmasString.toBoolean()
            val agentsJsonEncoded = backStackEntry.arguments?.getString("agentsJson") ?: ""

            val themeTitle =
                try {
                    URLDecoder.decode(themeTitleEncoded, "UTF-8")
                } catch (e: Exception) {
                    themeTitleEncoded
                }

            val themeDescription =
                try {
                    URLDecoder.decode(themeDescriptionEncoded, "UTF-8")
                } catch (e: Exception) {
                    themeDescriptionEncoded
                }

            val agentsJson =
                try {
                    URLDecoder.decode(agentsJsonEncoded, "UTF-8")
                } catch (e: Exception) {
                    agentsJsonEncoded
                }

            val viewModel: CollectionDetailVM = viewModel()

            LaunchedEffect(themeId, themeTitle, themeDescription, isChristmas, agentsJson) {
                val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
                val agentListType =
                    Types.newParameterizedType(List::class.java, AgentInfo::class.java)
                val agentListAdapter = moshi.adapter<List<AgentInfo>>(agentListType)

                val agents =
                    try {
                        if (agentsJson.isNotEmpty()) {
                            agentListAdapter.fromJson(agentsJson) ?: emptyList()
                        } else {
                            emptyList()
                        }
                    } catch (e: Exception) {
                        emptyList()
                    }

                viewModel.setThemeData(themeTitle, themeDescription, agents, isChristmas)
            }

            ThemedDetailScreen(
                viewModel = viewModel,
                onBack = { navController.popBackStack() },
                onClickAgent = { agent ->
                    AgentStore.addAgent(agent)
                    navController.navigate(Routes.chatPage(agent.id, false))
                },
            )
        }
    }
}
