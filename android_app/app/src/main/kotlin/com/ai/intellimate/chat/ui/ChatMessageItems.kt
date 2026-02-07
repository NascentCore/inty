package com.ai.intellimate.chat.ui

import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import com.ai.intellimate.utils.NetworkErrorHandler
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.ai.intellimate.R
import java.io.File

/**
 * 图片选择卡片组件
 *
 * 用于引导用户上传或拍摄照片作为参考，以便生成的图片更像用户本人。 显示一个带背景插画的卡片，包含标题、描述和三个操作按钮（选择照片、拍照、跳过）。
 *
 * @param onSkip 跳过按钮的回调
 * @param onImageSelected 图片选择回调，参数为选中的图片URI
 * @param modifier 修饰符
 *
 * 使用示例：
 *
 * ```
 * ImagePickItem(
 *     onSkip = { /* 处理跳过逻辑 */ },
 *     onImageSelected = { uri ->
 *         // 处理选中的图片
 *     }
 * )
 * ```
 */
@Composable
fun ImagePickItem(
    isLoading: Boolean,
    onSkip: () -> Unit,
    onImageSelected: (Uri) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    // 创建临时文件用于拍照
    var tempTakePic by remember { mutableStateOf<Uri?>(null) }

    // 相册选择器
    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
            uri?.let { onImageSelected(it) }
        }

    // 相机拍照
    val cameraLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
            if (success) {
                tempTakePic?.let { onImageSelected(it) }
            }
        }

    Box(modifier = modifier, contentAlignment = Alignment.BottomCenter) {
        Image(
            painter = painterResource(R.drawable.bg_message_image_picker),
            contentDescription = "bg",
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxSize().clip(RoundedCornerShape(16.dp)),
        )

        if (isLoading) {
            CircularProgressIndicator(
                color = Color.White,
                modifier = Modifier.align(Alignment.Center),
            )
        } else {
            // 内容层
            Column(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = stringResource(R.string.image_pick_protagonist_title),
                    style = MaterialTheme.typography.titleSmall,
                    textAlign = TextAlign.Center,
                    color = Color.White,
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = stringResource(R.string.image_pick_reference_description),
                    style = MaterialTheme.typography.bodySmall,
                    textAlign = TextAlign.Center,
                    color = Color.White.copy(alpha = 0.8f),
                )
                Spacer(Modifier.height(6.dp))
                Button(
                    onClick = {
                        val pickRequest =
                            PickVisualMediaRequest.Builder()
                                .setMediaType(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                .build()

                        galleryLauncher.launch(pickRequest)
                    },
                    colors =
                        ButtonDefaults.buttonColors(
                            containerColor = Color.White,
                            contentColor = Color.Black,
                        ),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.image_picker_gallery))
                }
                Button(
                    onClick = {
                        try {
                            val file =
                                File.createTempFile(
                                    "${System.currentTimeMillis()}",
                                    ".jpg",
                                    context.cacheDir,
                                )
                            tempTakePic =
                                FileProvider.getUriForFile(
                                        context,
                                        "${context.packageName}.provider",
                                        file,
                                    )
                                    .also { cameraLauncher.launch(it) }
                        } catch (error: Throwable) {
                            // #region agent log
                            val msg = error.localizedMessage.orEmpty()
                            NetworkErrorHandler.reportTlsParseToCrashlyticsIfRelevant("H", "ChatMessageItems.kt:camera", msg)
                            // #endregion
                            LogUtils.e(error.localizedMessage)
                            ToastUtils.showShort(msg)
                        }
                    },
                    colors =
                        ButtonDefaults.buttonColors(
                            containerColor = Color.White,
                            contentColor = Color.Black,
                        ),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.image_picker_camera))
                }
                OutlinedButton(
                    onClick = onSkip,
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(stringResource(R.string.image_pick_skip))
                }
            }
        }
    }
}

@Preview(showBackground = false, showSystemUi = true)
@Composable
fun ImagePickItemPreview() {
    IntelliMateTheme {
        ImagePickItem(
            isLoading = false,
            onSkip = {},
            onImageSelected = {},
            modifier = Modifier.size(210.5.dp, 312.5.dp),
        )
    }
}
