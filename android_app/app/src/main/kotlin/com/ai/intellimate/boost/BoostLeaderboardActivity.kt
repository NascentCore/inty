/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.services.AgentService
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.navigation.compose.rememberNavController
import com.ai.intellimate.R
import com.ai.intellimate.boost.ui.BoostLeaderboardTab
import com.ai.intellimate.chat.ChatActivity
import com.ai.intellimate.ui.components.EmptyStateComponent
import com.ai.intellimate.ui.components.EmptyStateType

/** Boost 排行榜的独立页面 */
class BoostLeaderboardActivity : BaseActivity() {

    companion object {
        fun launch(context: Context) {
            context.startActivity(Intent(context, BoostLeaderboardActivity::class.java))
        }
    }

    override fun getPageName(): String = "BoostLeaderboardPage"

    @Composable
    override fun ConfigComposeUI() {
        val navController = rememberNavController()
        BoostLeaderboardScreen(navController, onClick = {finish()})
    }
}
