package com.ai.inty.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable

/**
 * 解锁更多聊天的拦截弹窗
 */

@Composable
private fun OpenChatDialog(
    isUnlimited: Boolean = false,
    dialogData: ChatDialogData,
    onCancel: () -> Unit = {},
    onSure: () -> Unit = {},
    onMoreInfo: () -> Unit = {},
) {
    Dialog(onDismissRequest = onCancel) {
        Box(modifier = Modifier.clip(RoundedCornerShape(20.dp))) {
            Image(
                painter = painterResource(dialogData.imageRes),
                contentDescription = "",
                contentScale = ContentScale.Crop,
                modifier = Modifier.matchParentSize(),
            )
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 18.dp, vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
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
                    text = stringResource(R.string.heartmate_premium_full),
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
                    text = stringResource(R.string.auto_renews_cancel_full),
                    fontSize = 13.sp,
                    lineHeight = 20.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color(0xFFFFFFFF),
                    textAlign = TextAlign.Center,
                )
                Text(
                    text = stringResource(R.string.more_information_full),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Normal,
                    color = Color(0x59FFFFFF),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.noRippleClickable(onClick = onMoreInfo)
                )
            }
            IconButton(onClick = onCancel, Modifier.align(Alignment.TopEnd)) {
                Image(
                    painter = painterResource(R.drawable.close),
                    contentDescription = "",
                )
            }
        }
    }
}

/**
 * 弹窗内容信息
 */
internal data class ChatDialogData(
    val imageRes: Int,
    val content: String,
    val btnText: String,
)


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
    val data = ChatDialogData(
        R.drawable.img_unlimit_dialog_bg,
        stringResource(R.string.str_unlimit_dialog_content),
        stringResource(R.string.str_unlimit_btn_text)
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
    val data = ChatDialogData(
        R.drawable.img_advanced_model_dialog_bg,
        stringResource(R.string.str_premium_mode_dialog_content),
        stringResource(R.string.settings_premium_model)
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
    val data = ChatDialogData(
        R.drawable.img_premium_dialog_bg,
        stringResource(R.string.str_premium_chat_dialog_content),
        stringResource(R.string.str_beeter_ai_responeses)
    )
    PremiumChatDialog(data)
}

@Composable
internal fun HeartPrimaryButton(
    btnText: String,
    enable: Boolean = true,
    onClick: () -> Unit = {},
) {

    Box(
        modifier = Modifier
            .fillMaxWidth(.95f)
            .height(50.dp)
            .clip(RoundedCornerShape(25.dp))
            .alpha(if (enable) 1f else .4f)
            .background(
                brush = Brush.horizontalGradient(
                    colors = listOf(
                        Color(0xFFC122FF),
                        Color(0xFFFF905D),
                    )
                )
            )
            .clickable(enabled = enable, onClick = onClick),
        contentAlignment = Alignment.Center
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
