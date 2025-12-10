/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.utils.ToastUtils
import android.content.Context
import android.content.Intent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import com.ai.intellimate.R
import com.ai.intellimate.boost.ui.BoostLeaderboardTab
import com.ai.intellimate.chat.ChatActivity

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
        BoostLeaderboardScreen(onBack = { finish() })
    }
}

@Composable
private fun BoostLeaderboardScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val boostState by BoostManager.boostState.collectAsState()
    val leaderboard by BoostManager.leaderboard.collectAsState()

    val handleLeaderboardAction =
        remember(context) {
            { entry: BoostLeaderboardEntry, showSheet: Boolean ->
                if (entry.isSeed || entry.agentId.isBlank()) {
                    ToastUtils.showShort(R.string.boost_seed_placeholder_toast)
                } else {
                    ChatActivity.launch(
                        context,
                        agentInfo = null,
                        agentId = entry.agentId,
                        pageSource = ChatActivity.EXPLORE_TAB,
                        showBoostSheet = showSheet,
                    )
                }
            }
        }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.boost_leaderboard_title),
                        color = Color.White,
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.Rounded.ArrowBack,
                            contentDescription = stringResource(R.string.boost_leaderboard_back_cd),
                            tint = Color.White,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )
        },
    ) { innerPadding ->
        BoostLeaderboardTab(
            modifier = Modifier.padding(innerPadding).fillMaxSize(),
            availablePoints = boostState.availablePoints,
            entries = leaderboard,
            onChat = { handleLeaderboardAction(it, false) },
            onBoost = { handleLeaderboardAction(it, true) },
        )
    }
}
