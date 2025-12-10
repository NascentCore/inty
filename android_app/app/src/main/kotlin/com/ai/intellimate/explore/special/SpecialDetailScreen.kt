package com.ai.intellimate.explore.special

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.HeartTopAppBar
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shadow
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** 主题详情页面 */
@Composable
fun ThemedDetailScreen(
    viewModel: SpecialDetailVM,
    onBack: () -> Unit,
    onClickAgent: (AgentInfo) -> Unit,
) {
    val themeTitle by viewModel.themeTitle.collectAsState()
    val eventDescription by viewModel.eventDescription.collectAsState()
    val agents by viewModel.agents.collectAsState()
    val isChristmas by viewModel.isChristmas.collectAsState()

    Box(modifier = Modifier.fillMaxSize().background(HeartColor.primaryColor)) {
        Column(modifier = Modifier.fillMaxSize()) {
            HeartTopAppBar(
                title = themeTitle,
                onBack = onBack,
                titleTextStyle =
                    TextStyle(
                        fontSize = 20.sp,
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        shadow =
                            Shadow(
                                color = Color(0xFF8C8992),
                                offset = Offset(5f, 3f),
                                blurRadius = 15f,
                            ),
                    ),
            )

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(bottom = 16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                item { EventCard(description = eventDescription, isChristmas = isChristmas) }

                items(agents) { agent ->
                    ThemedCharacterCard(agent = agent, onClick = { onClickAgent(agent) })
                }
            }
        }
    }
}
