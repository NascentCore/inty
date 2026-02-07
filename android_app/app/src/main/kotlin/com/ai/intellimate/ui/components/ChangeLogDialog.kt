package com.ai.intellimate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.window.Dialog
import com.ai.intellimate.R
import com.ai.intellimate.changelog.ChangeLogEntry
import com.ai.intellimate.ui.UiConfigs

/**
 * CREATED_BY_AGENT: gpt-5.2-codex-high
 *
 * 变更日志弹窗。
 *
 * 使用范围：
 * - 仅在“我的”页面点击顶部时间线图标时展示。
 *
 * 预期视觉效果：
 * - 深色圆角卡片浮层，顶部标题 + 关闭按钮。
 * - 内容区域支持滚动，按版本分组显示日期与要点列表。
 * - 加载中显示居中进度指示，空列表显示提示文案。
 *
 * 可配置项：
 * - logs: 变更日志列表（按顺序展示）。
 * - isLoading: 控制加载态展示。
 * - onDismiss: 关闭弹窗回调。
 * - modifier: 外层容器样式扩展。
 */
@Composable
fun ChangeLogDialog(
    logs: List<ChangeLogEntry>,
    isLoading: Boolean,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier =
                modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.Shape.DialogLarge))
                    .background(color = UiConfigs.Colors.DialogSurface)
                    .padding(UiConfigs.Padding.DialogInner)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResource(R.string.change_logs_title),
                    fontSize = UiConfigs.Typography.BodyLarge,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )
                Spacer(Modifier.weight(1f))
                IconButton(onClick = onDismiss) {
                    Icon(
                        painter = painterResource(R.drawable.close),
                        contentDescription = stringResource(R.string.close),
                        tint = Color.White,
                    )
                }
            }

            Spacer(Modifier.height(UiConfigs.Spacing.Medium))

            when {
                isLoading -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                    ) {
                        CircularProgressIndicator(color = Color.White)
                    }
                }
                logs.isEmpty() -> {
                    Text(
                        text = stringResource(R.string.change_logs_empty),
                        fontSize = UiConfigs.Typography.Body,
                        color = Color.White.copy(alpha = UiConfigs.Alpha.SecondaryText),
                    )
                }
                else -> {
                    LazyColumn(
                        modifier =
                            Modifier.fillMaxWidth().heightIn(max = UiConfigs.Size.ChatDialogMinHeight),
                        verticalArrangement = Arrangement.spacedBy(UiConfigs.Spacing.Medium),
                    ) {
                        itemsIndexed(logs, key = { _, entry -> entry.id ?: entry.versionName }) {
                            _, entry ->
                            ChangeLogEntryBlock(entry = entry)
                        }
                    }
                }
            }
        }
    }
}

/**
 * 单条变更日志块。
 *
 * 使用范围：
 * - 仅在变更日志弹窗列表内部使用。
 *
 * 预期视觉效果：
 * - 顶部为版本号，下面可选显示发布日期。
 * - 以缩进的要点列表展示本次更新内容。
 *
 * 可配置项：
 * - entry: 单条变更日志数据。
 * - modifier: 外层容器样式扩展。
 */
@Composable
private fun ChangeLogEntryBlock(
    entry: ChangeLogEntry,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier,
        verticalArrangement = Arrangement.spacedBy(UiConfigs.Spacing.Small),
    ) {
        Text(
            text = entry.versionName,
            fontSize = UiConfigs.Typography.BodyLarge,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
        entry.releaseDate?.takeIf { it.isNotBlank() }?.let { releaseDate ->
            Text(
                text = stringResource(R.string.change_logs_release_date, releaseDate),
                fontSize = UiConfigs.Typography.Support,
                color = Color.White.copy(alpha = UiConfigs.Alpha.SecondaryText),
            )
        }
        if (entry.highlights.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(UiConfigs.Spacing.Tiny)) {
                entry.highlights.forEach { item ->
                    Text(
                        text = stringResource(R.string.change_logs_item_prefix, item),
                        fontSize = UiConfigs.Typography.Body,
                        color = Color.White.copy(alpha = UiConfigs.Alpha.SecondaryText),
                    )
                }
            }
        }
    }
}
