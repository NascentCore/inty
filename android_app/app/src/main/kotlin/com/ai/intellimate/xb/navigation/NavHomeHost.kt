package com.ai.intellimate.xb.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.compose.composable
import com.ai.intellimate.agent.heartbeat.heartbeat
import com.ai.intellimate.agent.info.AgentInfoViewModel
import com.ai.intellimate.agent.info.AiAgentInfoScreen
import com.ai.intellimate.agent.info.PhotoAlbumScreen
import com.ai.intellimate.login.RegInfoPage
import com.ai.intellimate.xb.helper.AgentStore

fun NavGraphBuilder.homeGraph(
    navController: NavController,
    agentInfoViewModel: AgentInfoViewModel,
) {

    // AI人设信息详情页面
    composable(Routes.Home.AgentInfoPage) { backStackEntry ->
        val agentId = backStackEntry.arguments?.getString("agentId")
        val agentInfo = AgentStore.getAgent(agentId = agentId)
        val agent by agentInfoViewModel.agentInfo.collectAsState()

        LaunchedEffect(agentId) {
            if (agentInfo != null) {
                agentInfoViewModel.setAgentInfo(agentInfo)
            } else {
                agentInfoViewModel.setAgentID(agentId!!)
            }
        }

        agent?.let {
            val galleryImages = agentInfoViewModel.chatImageGallery.collectAsState()

            AiAgentInfoScreen(
                agent = it,
                galleryItems = galleryImages.value,
                navController = navController,
            )
        }
    }

    composable(Routes.Home.AgentPhotoAlbum) { backStackEntry ->
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
                navController,
                agent = agentInfo,
                galleryItems = galleryImages.value,
                onBack = { navController.popBackStack() },
            )
        } else {
            Box {}
        }
    }

    /** 首次登录时完善个人信息页面 */
    composable(Routes.Home.RegInfoPage) { RegInfoPage(navController) }

    heartbeat(onBack = { navController.popBackStack() })
}
