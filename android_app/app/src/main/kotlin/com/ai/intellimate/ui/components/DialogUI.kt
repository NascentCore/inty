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
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.ai.intellimate.R
import com.ai.intellimate.settings.playStoreUrl
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
                    Modifier.align(Alignment.CenterHorizontally)
                        .focusRequester(cancelFocusRequester),
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

/**
 * 权限被用户明确拒绝且系统不再弹窗时的引导对话框。
 *
 * 使用场景：权限申请返回拒绝，并且系统不再显示授权弹窗（例如勾选“不再询问”）。用于提示用户
 * 前往系统设置手动开启权限，保证功能正常使用。
 *
 * 视觉效果：居中弹窗，标题 + 说明文案 + 主按钮（去设置开启）+ 次按钮（取消/稍后）。
 *
 * 可配置项：标题、说明文案、主/次按钮文案，以及点击回调。
 */
@Composable
fun PermissionSettingsDialog(
    title: String,
    description: String,
    confirmText: String,
    cancelText: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.Shape.Dialog))
                    .background(color = UiConfigs.Colors.DialogSurface)
                    .padding(UiConfigs.Padding.DialogInner)
        ) {
            Text(
                text = title,
                fontSize = UiConfigs.Typography.Title,
                color = Color.White,
            )

            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            Text(
                text = description,
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
                    text = confirmText,
                    fontSize = UiConfigs.Typography.ButtonLarge,
                    color = Color.White,
                )
            }

            TextButton(
                onClick = onDismiss,
                modifier = Modifier.align(Alignment.CenterHorizontally),
            ) {
                Text(
                    text = cancelText,
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
fun UpgradeDialog(
    title: String,
    content: String,
    onDismiss: () -> Unit,
    isForced: Boolean = false,
) {
    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(false, false, true)) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(RoundedCornerShape(UiConfigs.Shape.DialogLarge))
                    .background(color = UiConfigs.Colors.DialogSurface)
                    .padding(UiConfigs.Padding.DialogInner)
        ) {
            Text(
                text = title,
                fontSize = UiConfigs.Typography.Title,
                color = Color.White,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Center,
            )

            Spacer(Modifier.height(UiConfigs.Spacing.Small))

            Text(text = content, fontSize = UiConfigs.Typography.Body, color = Color.White)

            Spacer(Modifier.height(UiConfigs.Spacing.MediumPlus))

            val url = playStoreUrl()
            val localUriHandler = LocalUriHandler.current

            Button(
                onClick = { localUriHandler.openUri(url) },
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

            if (!isForced) {
                TextButton(
                    onClick = onDismiss,
                    modifier = Modifier.align(Alignment.CenterHorizontally),
                ) {
                    Text(
                        text = stringResource(R.string.str_cancel_upgrade),
                        fontSize = UiConfigs.Typography.Body,
                        color = Color.White,
                    )
                }
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun PreviewForceUpgradeDialog() {
    UpgradeDialog(title = "test", content = "test", onDismiss = {}, isForced = true)
}
