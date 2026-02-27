package com.ai.intellimate.xb.navigation

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.compose.composable
import com.ai.intellimate.boost.BoostLeaderboardScreen
import com.ai.intellimate.explore.special.CollectionDetailVM
import com.ai.intellimate.explore.special.ThemedDetailScreen
import com.ai.intellimate.xb.helper.AgentStore
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.net.URLDecoder

fun NavGraphBuilder.exploreGraph(navController: NavController) {
    composable(Routes.Explore.BoostLeaderboard) { BoostLeaderboardScreen(navController) }

    // 定义角色专区详情页面路由
    composable(Routes.Explore.CollectionDetail) { backStackEntry ->
        val themeId = backStackEntry.arguments?.getString("themeId") ?: ""
        val themeTitleEncoded = backStackEntry.arguments?.getString("themeTitle") ?: ""
        val themeDescriptionEncoded = backStackEntry.arguments?.getString("themeDescription") ?: ""
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
            val agentListType = Types.newParameterizedType(List::class.java, AgentInfo::class.java)
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
                navController.navigate(
                    Routes.Chat.chatPage(
                        agent.id,
                        false,
                        shouldAutoFocusInput = false,
                        fromPage = "themed_detail",
                    )
                )
            },
        )
    }
}
