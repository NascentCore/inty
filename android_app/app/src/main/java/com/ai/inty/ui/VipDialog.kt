package com.ai.inty.ui

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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable

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
                    .heightIn(430.dp)
                    .padding(horizontal = 24.dp)
                    .clip(RoundedCornerShape(8.dp))
        ) {
            Image(
                painter = painterResource(dialogData.imageRes),
                contentDescription = "",
                contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize(),
            )
            Column(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.SpaceBetween,
            ) {
                if (isUnlimited) {
                    Image(
                        painter = painterResource(R.drawable.img_king_premium),
                        contentDescription = "",
                    )
                    Spacer(Modifier.height(20.dp))
                } else {
                    Spacer(Modifier.height(170.dp))
                }
                Text(
                    text = stringResource(R.string.premium_subscription_title),
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(12.dp))
                Text(
                    text = dialogData.content,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color(0x8CFFFFFF),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp),
                )

                Spacer(Modifier.height(40.dp))
                HeartPrimaryButton(btnText = dialogData.btnText, onClick = onSure)
                Spacer(Modifier.height(12.dp))
                Text(
                    text = stringResource(R.string.auto_renews_cancel),
                    fontSize = 13.sp,
                    lineHeight = 20.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color(0xFFFFFFFF),
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = stringResource(R.string.more_information_full),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color(0x59FFFFFF),
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
internal fun AdvancedModelChatDialog(
    dialogData: ChatDialogData,
    onCancel: () -> Unit = {},
    onSure: () -> Unit = {},
    onMoreInfo: () -> Unit = {},
) {
    OpenChatDialog(false, dialogData, onCancel, onSure, onMoreInfo)
}

@Preview
@Composable
private fun PreviewAdvancedModelChatDialog() {
    val data =
        ChatDialogData(
            R.drawable.img_advanced_model_dialog_bg,
            stringResource(R.string.str_premium_mode_dialog_content),
            stringResource(R.string.premium_tag_on_chat_page),
        )
    AdvancedModelChatDialog(data)
}

@Composable
internal fun PremiumChatDialog(
    dialogData: ChatDialogData,
    onCancel: () -> Unit = {},
    onSure: () -> Unit = {},
    onMoreInfo: () -> Unit = {},
) {
    OpenChatDialog(false, dialogData, onCancel, onSure, onMoreInfo)
}

@Preview
@Composable
private fun PreviewPremiumChatDialog() {
    val data =
        ChatDialogData(
            R.drawable.img_premium_dialog_bg,
            stringResource(R.string.str_premium_chat_dialog_content),
            stringResource(R.string.str_beeter_ai_responeses),
        )
    PremiumChatDialog(data)
}

@Composable
internal fun HeartPrimaryButton(btnText: String, enable: Boolean = true, onClick: () -> Unit = {}) {

    Box(
        modifier =
            Modifier.fillMaxWidth(.95f)
                .height(50.dp)
                .clip(RoundedCornerShape(25.dp))
                .alpha(if (enable) 1f else .4f)
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors = listOf(Color(0xFFC122FF), Color(0xFFFF905D))
                        )
                )
                .clickable(enabled = enable, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = btnText,
            fontSize = 16.sp,
            lineHeight = 22.sp,
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
            modifier = Modifier.fillMaxWidth().heightIn(min = 300.dp).padding(vertical = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            Image(painter = painterResource(R.drawable.img_king_premium), contentDescription = "")
            Spacer(Modifier.height(30.dp))
            Text(
                text = stringResource(R.string.become_a_premium),
                fontSize = 22.sp,
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
        Box(modifier = Modifier.clip(RoundedCornerShape(20.dp))) {
            Image(
                painter = painterResource(dialogData.imageRes),
                contentDescription = "",
                contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize(),
            )
            Column(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Image(
                    painter = painterResource(R.drawable.img_king_premium),
                    contentDescription = "",
                )
                Spacer(Modifier.height(20.dp))

                Text(
                    text = stringResource(R.string.premium_subscription_title),
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(12.dp))
                Text(
                    text = dialogData.content,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color(0x8CFFFFFF),
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(40.dp))
                HeartPrimaryButton(btnText = dialogData.btnText, onClick = onSure)
                Spacer(Modifier.height(12.dp))
                Text(
                    text = stringResource(R.string.cancel),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color(0x59FFFFFF),
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
    maxLength: Int = 1000,
    onDismiss: () -> Unit,
    onSave: (String) -> Unit,
) {
    var replyStr by remember { mutableStateOf(inputStr) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        dragHandle = null,
        sheetState = sheetState,
        contentWindowInsets = { WindowInsets.waterfall },
    ) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .clip(RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp))
                    .background(
                        brush =
                            Brush.verticalGradient(
                                colors = listOf(Color(0xFF322341), Color(0xFF120E24))
                            )
                    )
                    .padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            IconButton(onClick = onDismiss, modifier = Modifier.align(Alignment.End)) {
                Image(painter = painterResource(R.drawable.close), contentDescription = "")
            }
            Text(
                text = stringResource(R.string.custom_reply_style),
                fontSize = 20.sp,
                lineHeight = 28.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(20.dp))
            HeartMultiLineEditor(
                Modifier.fillMaxWidth()
                    .height(168.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(Color(0x1AFFFFFF)),
                inputValue = replyStr,
                onInputChange = { replyStr = it },
                maxLength = maxLength,
                supportStr = "${replyStr.length}/$maxLength",
                hintStr = hintStr,
            )
            Spacer(Modifier.height(40.dp))
            HeartPrimaryButton(
                stringResource(R.string.save),
                enable = replyStr.isNotBlank(),
                onClick = { onSave(replyStr) },
            )
            Spacer(Modifier.height(40.dp))
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
