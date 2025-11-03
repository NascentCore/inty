package com.ai.intellimate.messages

import ai.sxwl.android.data.api.model.ConversationItem
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.zIndex
import com.ai.intellimate.R

@Composable
fun ConversationItemMenu(
    conversation: ConversationItem,
    isPinned: Boolean,
    isHidden: Boolean,
    onPinClick: () -> Unit,
    onHideClick: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Box(
        modifier = modifier
            .zIndex(1000f)
            .background(
                Color(0xCC000000),
                RoundedCornerShape(8.dp)
            ),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth(),
        ) {
            // Pin/Unpin 选项
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
                    .clickable {
                        onPinClick()
                        onDismiss()
                    }
                    .padding(horizontal = 16.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Start,
            ) {
                androidx.compose.foundation.Image(
                    painter = painterResource(R.drawable.ic_pin),
                    contentDescription = null,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(modifier = Modifier.width(12.dp))
                Text(
                    text = if (isPinned) stringResource(R.string.unpin) else stringResource(R.string.pin),
                    color = Color.White,
                    fontSize = 14.sp,
                )
            }

            // 分隔线
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(Color.White.copy(alpha = 0.2f)),
            )

            // Hide/Unhide 选项
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(48.dp)
                    .clickable {
                        onHideClick()
                        onDismiss()
                    }
                    .padding(horizontal = 16.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Start,
            ) {
                androidx.compose.foundation.Image(
                    painter = painterResource(R.drawable.ic_hide),
                    contentDescription = null,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(modifier = Modifier.width(12.dp))
                Text(
                    text = if (isHidden) stringResource(R.string.unhide) else stringResource(R.string.hide),
                    color = Color.White,
                    fontSize = 14.sp,
                )
            }
        }
    }
}

