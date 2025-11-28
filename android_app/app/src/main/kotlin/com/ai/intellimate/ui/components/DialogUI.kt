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
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

/** 删除账号确认对话框 */
@Composable
fun DeleteAccountDialog(onDismiss: () -> Unit, onConfirm: () -> Unit) {
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.Shape.Dialog))
                    .background(color = UiConfigs.Colors.DialogSurface)
                    .padding(UiConfigs.Padding.DialogInner)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResource(R.string.are_you_sure),
                    fontSize = UiConfigs.Typography.Title,
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
                text = stringResource(R.string.delete_account_warning),
                fontSize = UiConfigs.Typography.Body,
                color = Color.White,
            )

            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            Text(
                text = stringResource(R.string.please_read_warning),
                fontSize = UiConfigs.Typography.BodyLarge,
                color = Color.White,
            )

            Spacer(Modifier.height(UiConfigs.Spacing.MediumPlus))

            // 按钮
            Button(
                onClick = onDismiss,
                modifier =
                    Modifier.fillMaxWidth(UiConfigs.Fractions.DialogButtonWidth)
                        .align(Alignment.CenterHorizontally),
            ) {
                Text(
                    stringResource(R.string.cancel),
                    fontSize = UiConfigs.Typography.ButtonLarge,
                    color = Color.White,
                )
            }

            TextButton(
                onClick = onConfirm,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            ) {
                Text(
                    stringResource(R.string.delete),
                    fontSize = UiConfigs.Typography.Body,
                    color = Color.Red,
                )
            }
        }
    }
}

/** 退出登录确认对话框 */
@Composable
fun LogoutConfirmDialog(onDismiss: () -> Unit, onConfirm: () -> Unit) {
    val cancelFocusRequester = remember { FocusRequester() }

    LaunchedEffect(Unit) { cancelFocusRequester.requestFocus() }

    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.Shape.Dialog))
                    .background(color = UiConfigs.Colors.DialogSurface)
                    .padding(UiConfigs.Padding.DialogInner)
        ) {
            Text(
                text = stringResource(R.string.logout_confirm_title),
                fontSize = UiConfigs.Typography.Title,
                color = Color.White,
            )

            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            Text(
                text = stringResource(R.string.logout_confirm_description),
                fontSize = UiConfigs.Typography.Body,
                color = Color.White,
            )

            Spacer(Modifier.height(UiConfigs.Spacing.MediumPlus))

            Button(
                onClick = onConfirm,
                modifier =
                    Modifier.fillMaxWidth(UiConfigs.Fractions.DialogButtonWidth)
                        .align(Alignment.CenterHorizontally),
            ) {
                Text(
                    text = stringResource(R.string.logout),
                    fontSize = UiConfigs.Typography.ButtonLarge,
                    color = Color.White,
                )
            }

            TextButton(
                onClick = onDismiss,
                modifier =
                    Modifier.align(Alignment.CenterHorizontally).focusRequester(cancelFocusRequester)
            ) {
                Text(
                    text = stringResource(R.string.cancel),
                    fontSize = UiConfigs.Typography.Body,
                    color = Color.White,
                )
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun DeleteAccountDialogPreview() {
    DeleteAccountDialog(onDismiss = {}, onConfirm = {})
}

@Preview(showBackground = true)
@Composable
private fun LogoutConfirmDialogPreview() {
    LogoutConfirmDialog(onDismiss = {}, onConfirm = {})
}

/** App强制更新的Dialog */
@Composable
fun ForceUpgradeDialog(
    content: String = stringResource(R.string.str_upgrade_content),
    onDismiss: () -> Unit = {},
    onConfirm: () -> Unit = {},
) {
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(false, false, true)) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.Shape.DialogLarge))
                    .background(color = UiConfigs.Colors.DialogSurface)
                    .padding(UiConfigs.Padding.DialogInner)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResource(R.string.str_upgrade_required),
                    fontSize = UiConfigs.Typography.Title,
                    color = Color.White,
                )
                Spacer(Modifier.weight(1f))
                IconButton(onClick = onDismiss, enabled = false) {}
            }

            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            Text(text = content, fontSize = UiConfigs.Typography.Body, color = Color.White)

            Spacer(Modifier.height(UiConfigs.Spacing.MediumPlus))

            // 按钮
            Button(
                onClick = onConfirm,
                modifier =
                    Modifier.fillMaxWidth(UiConfigs.Fractions.DialogButtonWidth)
                        .align(Alignment.CenterHorizontally),
            ) {
                Text(
                    stringResource(R.string.str_upgrade_now),
                    fontSize = UiConfigs.Typography.ButtonLarge,
                    color = Color.White,
                )
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun PreviewForceUpgradeDialog() {
    ForceUpgradeDialog(onDismiss = {}, onConfirm = {})
}
