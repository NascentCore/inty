/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.leaderboard.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import com.ai.intellimate.R

/**
 * Top Users 子榜单
 *
 * 使用范围：Leaderboard 页面内的"Top Users"子 Tab。
 * 预期视觉效果：居中显示"Under Development"文本，表示该功能正在开发中。
 *
 * 可配置项：
 * - modifier：外部容器尺寸控制
 */
@Composable
fun TopUsersLeaderboardTab(
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier.fillMaxSize(),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = stringResource(R.string.under_development),
            color = Color.White,
            style = MaterialTheme.typography.titleLarge,
            textAlign = TextAlign.Center,
        )
    }
}

