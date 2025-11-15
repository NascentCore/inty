package com.ai.intellimate.ui

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.ui.HeartMultiLineEditor
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.waterfall
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.SheetState
import androidx.compose.material3.SheetValue
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.material3.rememberStandardBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.ai.intellimate.R

/** 解锁更多聊天的拦截弹窗 */
@Composable
private fun OpenChatDialog(
    isUnlimited: Boolean = false,
    dialogData: ChatDialogData,
    onCancel: () -> Unit = {},
    onSure: () -> Unit = {},
    onMoreInfo: () -> Unit = {},
) {
    Dialog(
        onDismissRequest = onCancel,
        properties =
            DialogProperties(
                dismissOnBackPress = false,
                dismissOnClickOutside = false,
                usePlatformDefaultWidth = false,
            ),
    ) {
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .heightIn(UiConfigs.Size.ChatDialogMinHeight)
                    .padding(horizontal = UiConfigs.Padding.DialogEdge)
                    .clip(RoundedCornerShape(UiConfigs.Shape.VipDialog))
        ) {
            Image(
                painter = painterResource(dialogData.imageRes),
                contentDescription = "",
                contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize(),
            )
            Column(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(
                            horizontal = UiConfigs.Padding.DialogContentHorizontal,
                            vertical = UiConfigs.Padding.DialogContentVertical,
                        ),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                if (isUnlimited) {
                    Image(
                        painter = painterResource(R.drawable.img_king_premium),
                        contentDescription = "",
                    )
                    Spacer(Modifier.height(UiConfigs.Spacing.Large))
                } else {
                    Spacer(Modifier.height(UiConfigs.Spacing.VipHeroPlaceholder))
                }
                Text(
                    text = stringResource(R.string.premium_subscription_title),
                    fontSize = UiConfigs.Typography.Title,
                    fontWeight = FontWeight.Normal,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(UiConfigs.Spacing.Medium))
                // 对文案中第一个 "!" 之前的语句进行加粗
                val annotatedContent = buildAnnotatedString {
                    val content = dialogData.content
                    val firstExclamationIndex = content.indexOf('!')
                    if (firstExclamationIndex >= 0) {
                        // 找到第一个 "!"，加粗从开头到 "!" 的部分（包含 "!"）
                        val boldText = content.take(firstExclamationIndex + 1)
                        val remainingText = content.substring(firstExclamationIndex + 1)

                        // 加粗部分
                        withStyle(style = SpanStyle(fontWeight = FontWeight.Bold)) {
                            append(boldText)
                        }
                        // 剩余部分
                        append(remainingText)
                    } else {
                        // 如果没有找到 "!"，直接显示原文本
                        append(content)
                    }
                }
                Text(
                    text = annotatedContent,
                    fontSize = UiConfigs.Typography.Body,
                    fontWeight = FontWeight.Normal,
                    color = UiConfigs.Colors.VipSecondaryText,
                    textAlign = TextAlign.Center,
                    modifier =
                        Modifier.fillMaxWidth().padding(horizontal = UiConfigs.Padding.TextBlock),
                )

                Spacer(Modifier.height(UiConfigs.Spacing.XLarge))
                HeartPrimaryButton(btnText = dialogData.btnText, onClick = onSure)
                Spacer(Modifier.height(UiConfigs.Spacing.Medium))
                Text(
                    text = stringResource(R.string.auto_renews_cancel),
                    fontSize = UiConfigs.Typography.Support,
                    lineHeight = UiConfigs.LineHeight.Support,
                    fontWeight = FontWeight.Normal,
                    color = Color(0xFFFFFFFF),
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(UiConfigs.Spacing.Tiny))
                Text(
                    text = stringResource(R.string.more_information_full),
                    fontSize = UiConfigs.Typography.Caption,
                    fontWeight = FontWeight.Normal,
                    color = UiConfigs.Colors.VipTertiaryText,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.noRippleClickable(onClick = onMoreInfo),
                )
            }
            IconButton(onClick = onCancel, Modifier.align(Alignment.TopEnd)) {
                Image(painter = painterResource(R.drawable.close), contentDescription = "")
            }
        }
    }
}

/** 弹窗内容信息 */
internal data class ChatDialogData(val imageRes: Int, val content: String, val btnText: String)

@Composable
internal fun UnlimitChatDialog(
    dialogData: ChatDialogData,
    onCancel: () -> Unit = {},
    onSure: () -> Unit = {},
    onMoreInfo: () -> Unit = {},
) {
    OpenChatDialog(isUnlimited = true, dialogData, onCancel, onSure, onMoreInfo)
}

@Preview
@Composable
private fun PreviewUnlimitChatDialog() {
    val data =
        ChatDialogData(
            R.drawable.img_unlimit_dialog_bg,
            stringResource(R.string.str_unlimit_dialog_content),
            stringResource(R.string.str_unlimit_btn_text),
        )
    UnlimitChatDialog(data)
}

@Composable
internal fun HeartPrimaryButton(btnText: String, enable: Boolean = true, onClick: () -> Unit = {}) {

    Box(
        modifier =
            Modifier.fillMaxWidth(UiConfigs.Fractions.PrimaryButtonWidth)
                .height(UiConfigs.Size.PrimaryButtonHeight)
                .clip(RoundedCornerShape(UiConfigs.Shape.PrimaryButton))
                .alpha(if (enable) 1f else UiConfigs.Alpha.DisabledButton)
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors = UiConfigs.Colors.PrimaryGradient
                        )
                )
                .clickable(enabled = enable, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = btnText,
            fontSize = UiConfigs.Typography.Button,
            lineHeight = UiConfigs.LineHeight.Button,
            fontWeight = FontWeight.Normal,
            color = Color.White,
            textAlign = TextAlign.Center,
        )
    }
}

/** 购买会员成功的弹窗 */
@Preview
@Composable
internal fun BePremiumDialog(onDismiss: () -> Unit = {}) {
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .heightIn(min = UiConfigs.Size.BecomePremiumDialogMinHeight)
                    .padding(vertical = UiConfigs.Spacing.Large),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Image(painter = painterResource(R.drawable.img_king_premium), contentDescription = "")
            Spacer(Modifier.height(UiConfigs.Spacing.HeroGap))
            Text(
                text = stringResource(R.string.become_a_premium),
                fontSize = UiConfigs.Typography.Title,
                fontWeight = FontWeight.Normal,
                color = Color.White,
                textAlign = TextAlign.Center,
            )
        }
    }
}

/** 会员过期的弹窗提醒 */
@Composable
internal fun ExpiredVipDialog(
    dialogData: ChatDialogData,
    onCancel: () -> Unit = {},
    onSure: () -> Unit = {},
) {
    Dialog(
        onDismissRequest = onCancel,
        properties =
            DialogProperties(
                dismissOnBackPress = false,
                dismissOnClickOutside = false,
                usePlatformDefaultWidth = true,
            ),
    ) {
        Box(modifier = Modifier.clip(RoundedCornerShape(UiConfigs.Shape.DialogLarge))) {
            Image(
                painter = painterResource(dialogData.imageRes),
                contentDescription = "",
                contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize(),
            )
            Column(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(
                            horizontal = UiConfigs.Padding.DialogContentHorizontal,
                            vertical = UiConfigs.Padding.DialogContentVertical,
                        ),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Image(
                    painter = painterResource(R.drawable.img_king_premium),
                    contentDescription = "",
                )
                Spacer(Modifier.height(UiConfigs.Spacing.Large))

                Text(
                    text = stringResource(R.string.premium_subscription_title),
                    fontSize = UiConfigs.Typography.Title,
                    fontWeight = FontWeight.Normal,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(UiConfigs.Spacing.Medium))
                Text(
                    text = dialogData.content,
                    fontSize = UiConfigs.Typography.Body,
                    fontWeight = FontWeight.Normal,
                    color = UiConfigs.Colors.VipSecondaryText,
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(UiConfigs.Spacing.XLarge))
                HeartPrimaryButton(btnText = dialogData.btnText, onClick = onSure)
                Spacer(Modifier.height(UiConfigs.Spacing.Medium))
                Text(
                    text = stringResource(R.string.cancel),
                    fontSize = UiConfigs.Typography.Caption,
                    fontWeight = FontWeight.Normal,
                    color = UiConfigs.Colors.VipTertiaryText,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.noRippleClickable(onClick = onCancel),
                )
            }
            IconButton(onClick = onCancel, Modifier.align(Alignment.TopEnd)) {
                Image(painter = painterResource(R.drawable.close), contentDescription = "")
            }
        }
    }
}

@Preview
@Composable
private fun PreviewExpiredVipDialog() {
    val data =
        ChatDialogData(
            R.drawable.img_unlimit_dialog_bg,
            stringResource(R.string.str_expired_vip_dialog_content),
            stringResource(R.string.subscribe),
        )
    ExpiredVipDialog(data)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun ReplyStyleSheet(
    sheetState: SheetState = rememberModalBottomSheetState(),
    inputStr: String,
    hintStr: String = "",
    maxLength: Int = UiConfigs.Limits.DefaultTextFieldMaxChars,
    onDismiss: () -> Unit,
    onSave: (String) -> Unit,
) {
    var replyStr by remember(inputStr) { mutableStateOf(inputStr) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        dragHandle = null,
        sheetState = sheetState,
        contentWindowInsets = { WindowInsets.waterfall },
    ) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(
                        RoundedCornerShape(
                            topStart = UiConfigs.Shape.SheetTop,
                            topEnd = UiConfigs.Shape.SheetTop,
                        )
                    )
                    .background(
                        brush =
                            Brush.verticalGradient(
                                colors = UiConfigs.Colors.ReplySheetGradient
                            )
                    )
                    .padding(
                        horizontal = UiConfigs.Spacing.MediumPlus,
                        vertical = UiConfigs.Spacing.Small,
                    ),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            IconButton(onClick = onDismiss, modifier = Modifier.align(Alignment.End)) {
                Image(painter = painterResource(R.drawable.close), contentDescription = "")
            }
            Text(
                text = stringResource(R.string.custom_reply_style),
                fontSize = UiConfigs.Typography.SheetTitle,
                lineHeight = UiConfigs.LineHeight.SheetTitle,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(UiConfigs.Spacing.Large))
            HeartMultiLineEditor(
                Modifier.fillMaxWidth()
                    .height(UiConfigs.Size.ReplyEditorHeight)
                    .clip(RoundedCornerShape(UiConfigs.Shape.Input))
                    .background(UiConfigs.Colors.SheetSurfaceOverlay),
                inputValue = replyStr,
                onInputChange = { replyStr = it },
                maxLength = maxLength,
                supportStr = "${replyStr.length}/$maxLength",
                hintStr = hintStr,
            )
            Spacer(Modifier.height(UiConfigs.Spacing.XLarge))
            HeartPrimaryButton(
                stringResource(R.string.save),
                enable = replyStr.isNotBlank(),
                onClick = { onSave(replyStr) },
            )
            Spacer(Modifier.height(UiConfigs.Spacing.XLarge))
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Preview
@Composable
private fun PreviewReplyStyleSheet() {
    ReplyStyleSheet(
        sheetState = rememberStandardBottomSheetState(initialValue = SheetValue.Expanded),
        inputStr = "I'm a teacher ...",
        onDismiss = {},
        onSave = {},
    )
}
