package com.ai.inty.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.viewmodels.MainViewModel
import com.inty.utils.log.EasyLog

@Composable
fun RecommendPage(
    modifier: Modifier,
    agents: List<AgentInfo>,
    onClickAgent: (AgentInfo) -> Unit,
) {
//    val agents = viewModel.agentList
    Box(
        modifier = modifier
    ) {
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )
        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent
        ) { innerPadding ->

            Column {
                Spacer(Modifier.height(innerPadding.calculateTopPadding() + 28.dp))

                Row(
                    modifier = Modifier.padding(24.dp, 0.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IntyImage(
                        model = R.drawable.popular1
                    )
                    Spacer(Modifier.width(7.dp))
                    IntyImage(
                        model = R.drawable.popular
                    )
                }

                Spacer(Modifier.height(30.dp))

                LazyVerticalGrid(
                    modifier = Modifier.padding(bottom = innerPadding.calculateBottomPadding(), start = 16.dp, end = 16.dp),
                    columns = GridCells.Fixed(2),
                    horizontalArrangement = Arrangement.spacedBy(13.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    items(agents) { agent ->
                        RecommendPageItem(
                            modifier = Modifier.noRippleClickable {
                                onClickAgent(agent)
                            },
                            agentInfo = agent
                        )
                    }
                }
            }


        }
    }
}

@Composable
fun RecommendPageItem(
    modifier: Modifier,
    agentInfo: AgentInfo
) {
    Box(
        modifier = modifier.size(165.dp, 220.dp)
    ) {
        IntyImage(
            modifier = Modifier.fillMaxSize(),
            model = agentInfo.avatar,
            placeholder = painterResource(R.drawable.ic_launcher_background),
            error = painterResource(R.drawable.ic_launcher_background),
        )
        Text(
            modifier = Modifier.align(Alignment.BottomStart).padding(12.dp),
            text = agentInfo.name,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,

        )
    }
}