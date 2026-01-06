package com.ai.intellimate.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
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
import androidx.compose.ui.window.Dialog
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

/**
 * CREATED_BY_AGENT: cursor-gpt-5.2
 *
 * IntelliMate 使用小贴士弹窗。
 *
 * 使用范围：
 * - 仅用于“用户已登录后”的主流程提示（例如 App 打开时随机展示一条 tips）。
 *
 * 预期视觉效果：
 * - 与现有对话框一致的深色卡片底 + 圆角
 * - 顶部标题 + 右侧关闭按钮
 * - 正文展示一条 tip
 * - 底部一个主按钮（Got it）用于关闭
 */
@Composable
fun IntelliMateTipDialog(
    tipText: String,
    onDismiss: () -> Unit,
    onDisableTips: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier =
                modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.Shape.Dialog))
                    .background(color = UiConfigs.Colors.DialogSurface)
                    .padding(UiConfigs.Padding.DialogInner)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResource(R.string.intellimate_tip_title),
                    fontSize = UiConfigs.Typography.BodyLarge,
                    color = Color.White,
                )
                Spacer(Modifier.weight(1f))
                IconButton(onClick = onDismiss) {
                    Icon(
                        painter = painterResource(R.drawable.close),
                        contentDescription = "",
                        tint = Color.White,
                    )
                }
            }

            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            Text(
                text = tipText,
                fontSize = UiConfigs.Typography.Body,
                color = Color.White.copy(alpha = UiConfigs.Alpha.SecondaryText),
            )

            Spacer(Modifier.height(UiConfigs.Spacing.MediumPlus))

            Button(
                onClick = onDismiss,
                modifier =
                    Modifier.fillMaxWidth(UiConfigs.Fractions.DialogButtonWidth)
                        .align(Alignment.CenterHorizontally),
            ) {
                Text(
                    text = stringResource(R.string.intellimate_tip_got_it),
                    fontSize = UiConfigs.Typography.ButtonLarge,
                    color = Color.White,
                )
            }

            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            Button(
                onClick = {
                    onDisableTips()
                    onDismiss()
                },
                modifier =
                    Modifier.fillMaxWidth(UiConfigs.Fractions.DialogButtonWidth)
                        .align(Alignment.CenterHorizontally),
            ) {
                Text(
                    text = stringResource(R.string.intellimate_tip_disable),
                    fontSize = UiConfigs.Typography.ButtonLarge,
                    color = Color.White,
                )
            }
        }
    }
}
