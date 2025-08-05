package com.ai.inty.ui.components

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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.ai.inty.R

/**
 * 删除账号确认对话框
 */
@Composable
fun DeleteAccountDialog(
    onDismiss: () -> Unit,
    onConfirm: () -> Unit
) {
    Dialog(onDismissRequest = onDismiss) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(color = Color(0xFF1B0130))
                .padding(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Are you sure?",
                    fontSize = 22.sp,
                    color = Color.White
                )
                Spacer(Modifier.weight(1f))
                IconButton(onClick = onDismiss) {
                    Icon(
                        painter = painterResource(R.drawable.close),
                        contentDescription = "",
                        tint = Color.White
                    )
                }
            }

            Spacer(Modifier.height(8.dp))

            Text(
                text = "All your data including chats history and created AI characters will be lost, and cannot be restored.",
                fontSize = 14.sp,
                color = Color.White
            )

            Spacer(Modifier.height(8.dp))

            Text(
                text = "Please read the warning carefully and proceed with caution.",
                fontSize = 16.sp,
                color = Color.White
            )

            Spacer(Modifier.height(16.dp))

            // 按钮
            Button(
                onClick = onDismiss,
                modifier = Modifier
                    .fillMaxWidth(.85f)
                    .align(Alignment.CenterHorizontally)
            ) {
                Text("Cancel", fontSize = 18.sp, color = Color.White)
            }

            TextButton(
                onClick = onConfirm,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            ) {
                Text("Delete", fontSize = 14.sp, color = Color.Red)
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun DeleteAccountDialogPreview() {
    DeleteAccountDialog(
        onDismiss = {},
        onConfirm = {}
    )
} 
