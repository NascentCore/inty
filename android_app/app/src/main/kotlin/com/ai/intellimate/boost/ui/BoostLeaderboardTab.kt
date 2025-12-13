/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostLeaderboardEntry
import com.ai.intellimate.boost.BoostTrend
import com.ai.intellimate.ui.UiConfigs

@Composable
fun BoostLeaderboardTab(
    modifier: Modifier = Modifier,
    availablePoints: Int,
    entries: List<BoostLeaderboardEntry>,
    onChat: (BoostLeaderboardEntry) -> Unit,
    onBoost: (BoostLeaderboardEntry) -> Unit,
) {
    Column(
        modifier =
            modifier
                .fillMaxSize()
                .padding(
                    horizontal = UiConfigs.LeaderBoard.HorizontalPadding,
                    vertical = UiConfigs.LeaderBoard.VerticalPadding,
                )
    ) {
        BoostStatusChip(modifier = Modifier.fillMaxWidth(), availablePoints = availablePoints)

        Spacer(Modifier.height(UiConfigs.LeaderBoard.StatusChipToListSpacing))

        if (entries.isEmpty()) {
            Column(
                modifier =
                    Modifier.fillMaxSize()
                        .clip(RoundedCornerShape(UiConfigs.LeaderBoard.EmptyStateCardCornerRadius))
                        .background(Color(0xFF1A1A1F))
                        .padding(UiConfigs.LeaderBoard.EmptyStateCardPadding),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    text = stringResource(R.string.boost_leaderboard_empty),
                    color = Color.White.copy(alpha = 0.7f),
                    fontSize = 14.sp,
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(UiConfigs.LeaderBoard.ListItemSpacing),
            ) {
                itemsIndexed(entries, key = { _, item -> item.agentId + item.rank }) { index, entry
                    ->
                    BoostLeaderboardRow(
                        entry = entry,
                        onBoost = { onBoost(entry) },
                        onChat = { onChat(entry) },
                        showDivider = index < entries.lastIndex,
                    )
                }
                item { Spacer(Modifier.height(UiConfigs.LeaderBoard.ListBottomSpacing)) }
            }
        }
    }
}

@Composable
private fun BoostLeaderboardRow(
    entry: BoostLeaderboardEntry,
    onChat: () -> Unit,
    onBoost: () -> Unit,
    showDivider: Boolean,
) {
    Column(
        modifier =
            Modifier.fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFF15151A))
                .padding(16.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = "#${entry.rank}",
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp,
            )
            Spacer(Modifier.size(12.dp))
            AsyncImage(
                modifier = Modifier.size(48.dp).clip(CircleShape),
                model = ImageRequest.Builder(LocalContext.current).data(entry.avatarUrl).build(),
                placeholder = painterResource(R.drawable.img_default_avatar),
                error = painterResource(R.drawable.img_default_avatar),
                contentDescription = null,
            )
            Spacer(Modifier.size(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = entry.agentName,
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold,
                )
                Text(
                    text =
                        stringResource(
                            R.string.boost_leaderboard_energy_points_value,
                            entry.pointsInvested,
                        ),
                    color = Color.White.copy(alpha = 0.7f),
                    fontSize = 12.sp,
                )
            }
            TrendPill(entry)
        }
        Spacer(Modifier.height(12.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(
                onClick = onBoost,
                modifier = Modifier.weight(1f),
                colors =
                    ButtonDefaults.buttonColors(
                        containerColor = Color(0xFFFF7A18),
                        contentColor = Color.White,
                    ),
            ) {
                Text(text = stringResource(R.string.boost_sheet_confirm))
            }
            OutlinedButton(
                onClick = onChat,
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
            ) {
                Text(text = stringResource(R.string.boost_leaderboard_chat))
            }
        }
    }
    if (showDivider) {
        Spacer(Modifier.height(4.dp))
    }
}

@Composable
private fun TrendPill(entry: BoostLeaderboardEntry) {
    val (text, tint) =
        when (entry.trend) {
            BoostTrend.UP -> stringResource(R.string.boost_trend_up) to Color(0xFF5CF595)
            BoostTrend.DOWN -> stringResource(R.string.boost_trend_down) to Color(0xFFF96D7B)
            BoostTrend.FLAT -> stringResource(R.string.boost_trend_flat) to Color(0xFFA3A3B5)
        }
    Row(
        modifier =
            Modifier.clip(RoundedCornerShape(50))
                .background(tint.copy(alpha = 0.18f))
                .padding(horizontal = 12.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Image(
            painter =
                painterResource(
                    when (entry.trend) {
                        BoostTrend.UP -> R.drawable.ic_arrow_up
                        BoostTrend.DOWN -> R.drawable.ic_arrow_down
                        BoostTrend.FLAT -> R.drawable.ic_keep_talking // fallback icon
                    }
                ),
            contentDescription = null,
            modifier = Modifier.size(14.dp),
        )
        Spacer(Modifier.size(4.dp))
        Text(text = text, color = tint, fontSize = 12.sp)
    }
}
