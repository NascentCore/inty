package com.ai.intellimate.ui

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.ui.HeartPrimaryButton
import androidx.compose.foundation.Image
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.ai.intellimate.R

/** 反馈请求弹窗 */
@Composable
internal fun FeedbackRequestDialog(onCancel: () -> Unit = {}, onSendSuggestions: () -> Unit = {}) {
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
                painter = painterResource(R.drawable.img_unlimit_dialog_bg),
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
                Spacer(Modifier.height(50.dp))

                Text(
                    text = stringResource(R.string.feedback_title),
                    fontSize = UiConfigs.Typography.Title,
                    fontWeight = FontWeight.Normal,
                    color = Color.White,
                    textAlign = TextAlign.Center,
                )

                Spacer(Modifier.height(UiConfigs.Spacing.Medium))
                Text(
                    text = stringResource(R.string.feedback_request_content),
                    fontSize = UiConfigs.Typography.Body,
                    fontWeight = FontWeight.Normal,
                    color = UiConfigs.Colors.VipSecondaryText,
                    textAlign = TextAlign.Start,
                    modifier = Modifier.padding(start = 18.dp),
                )

                Spacer(Modifier.height(UiConfigs.Spacing.XLarge))
                HeartPrimaryButton(
                    btnText = stringResource(R.string.send_suggestions),
                    onClick = onSendSuggestions,
                )
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
private fun PreviewFeedBackDialog() {
    FeedbackRequestDialog()
}
