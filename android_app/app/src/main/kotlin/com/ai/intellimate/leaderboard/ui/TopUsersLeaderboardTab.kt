/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.leaderboard.ui

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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

/**
 * Top Users 子榜单
 *
 * 使用范围：Leaderboard 页面内的“Top Users”子 Tab。
 * 预期视觉效果：与 Top IntelliMates 榜单一致的深色卡片列表，展示用户头像、昵称与活跃度分数。
 *
 * 可配置项：
 * - modifier：外部容器尺寸/内边距控制
 * - entries：榜单条目（当前使用 dummy 数据，后续可替换为后端数据）
 */
@Composable
fun TopUsersLeaderboardTab(
    modifier: Modifier = Modifier,
    entries: List<TopUserLeaderboardEntry> = DUMMY_TOP_USERS,
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
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(UiConfigs.LeaderBoard.ListItemSpacing),
        ) {
            itemsIndexed(entries, key = { _, item -> item.userId }) { index, entry ->
                TopUserLeaderboardRow(
                    entry = entry.copy(rank = index + 1),
                    showDivider = index < entries.lastIndex,
                )
            }
            item { Spacer(Modifier.height(UiConfigs.LeaderBoard.ListBottomSpacing)) }
        }
    }
}

private val DUMMY_TOP_USERS: List<TopUserLeaderboardEntry> =
    listOf(
        TopUserLeaderboardEntry(
            rank = 1,
            userId = "u_1",
            displayName = "Nova",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_1/256/256",
            activityScore = 9820,
        ),
        TopUserLeaderboardEntry(
            rank = 2,
            userId = "u_2",
            displayName = "Mika",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_2/256/256",
            activityScore = 8840,
        ),
        TopUserLeaderboardEntry(
            rank = 3,
            userId = "u_3",
            displayName = "Aria",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_3/256/256",
            activityScore = 8010,
        ),
        TopUserLeaderboardEntry(
            rank = 4,
            userId = "u_4",
            displayName = "Leo",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_4/256/256",
            activityScore = 7340,
        ),
        TopUserLeaderboardEntry(
            rank = 5,
            userId = "u_5",
            displayName = "Sora",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_5/256/256",
            activityScore = 6920,
        ),
        TopUserLeaderboardEntry(
            rank = 6,
            userId = "u_6",
            displayName = "Eden",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_6/256/256",
            activityScore = 6400,
        ),
        TopUserLeaderboardEntry(
            rank = 7,
            userId = "u_7",
            displayName = "Ivy",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_7/256/256",
            activityScore = 5980,
        ),
        TopUserLeaderboardEntry(
            rank = 8,
            userId = "u_8",
            displayName = "Kai",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_8/256/256",
            activityScore = 5510,
        ),
        TopUserLeaderboardEntry(
            rank = 9,
            userId = "u_9",
            displayName = "Luna",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_9/256/256",
            activityScore = 5090,
        ),
        TopUserLeaderboardEntry(
            rank = 10,
            userId = "u_10",
            displayName = "Finn",
            avatarUrl = "https://picsum.photos/seed/leaderboard_user_10/256/256",
            activityScore = 4760,
        ),
    )

/**
 * Top Users 榜单条目（dummy / 后续可接入真实数据）
 *
 * - userId：唯一 ID，用于列表 key
 * - displayName：展示昵称
 * - avatarUrl：头像链接
 * - activityScore：活跃度分数（越大越靠前）
 */
data class TopUserLeaderboardEntry(
    val rank: Int,
    val userId: String,
    val displayName: String,
    val avatarUrl: String,
    val activityScore: Int,
)

@Composable
private fun TopUserLeaderboardRow(entry: TopUserLeaderboardEntry, showDivider: Boolean) {
    Column(
        modifier =
            Modifier.fillMaxWidth()
                .clip(RoundedCornerShape(UiConfigs.LeaderBoard.RowCardCornerRadius))
                .background(MaterialTheme.colorScheme.surfaceContainerHigh)
                .padding(UiConfigs.LeaderBoard.RowCardPadding)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                text = "#${entry.rank}",
                color = Color.White,
                style = MaterialTheme.typography.titleMedium,
            )
            Spacer(Modifier.size(UiConfigs.LeaderBoard.RankToAvatarSpacing))
            AsyncImage(
                modifier = Modifier.size(UiConfigs.LeaderBoard.AvatarSize).clip(CircleShape),
                model = ImageRequest.Builder(androidx.compose.ui.platform.LocalContext.current)
                    .data(entry.avatarUrl)
                    .build(),
                contentDescription = null,
            )
            Spacer(Modifier.size(UiConfigs.LeaderBoard.AvatarToNameSpacing))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = entry.displayName,
                    color = Color.White,
                    style = MaterialTheme.typography.titleMedium,
                )
                Text(
                    text =
                        stringResource(
                            R.string.leaderboard_top_users_activity_score,
                            entry.activityScore,
                        ),
                    color = Color.White.copy(alpha = 0.7f),
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
    }
    if (showDivider) {
        Spacer(Modifier.height(UiConfigs.LeaderBoard.RowDividerSpacing))
    }
}

