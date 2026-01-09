package com.ai.intellimate.ui.components

import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import java.io.File
import kotlin.io.path.createTempFile
import kotlinx.coroutines.launch

/**
 * 图片选择底部弹窗组件
 *
 * 提供相册、拍照、取消三个选项，使用系统提供的相册和相机功能。 当用户选择相册或拍照后，通过回调返回图片URI。
 *
 * @param onDismiss 关闭弹窗的回调
 * @param onImageSelected 图片选择回调，参数为选中的图片URI，如果为null表示用户取消选择
 * @param modifier 修饰符
 *
 * 使用示例：
 *
 * ```
 * var showImagePicker by remember { mutableStateOf(false) }
 *
 * if (showImagePicker) {
 *     ImagePickerBottomSheet(
 *         onDismiss = { showImagePicker = false },
 *         onImageSelected = { uri ->
 *             uri?.let {
 *                 // 处理选中的图片
 *             }
 *             showImagePicker = false
 *         }
 *     )
 * }
 * ```
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ImagePickerBottomSheet(
    onDismiss: () -> Unit,
    onImageSelected: (Uri) -> Unit,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

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

    LaunchedEffect(Unit) { sheetState.show() }

    ModalBottomSheet(
        onDismissRequest = {
            scope
                .launch { sheetState.hide() }
                .invokeOnCompletion {
                    if (!sheetState.isVisible) {
                        onDismiss()
                    }
                }
        },
        sheetState = sheetState,
        dragHandle = null,
        contentWindowInsets = { WindowInsets() },
        modifier = modifier,
    ) {
        Column(
            modifier =
                Modifier.fillMaxWidth().padding(vertical = UiConfigs.Padding.DialogContentVertical)
        ) {
            // 相册按钮
            ImagePickerOption(
                icon = Icons.Filled.PhotoLibrary,
                text = stringResource(R.string.image_picker_gallery),
                onClick = {
                    val pickRequest =
                        PickVisualMediaRequest.Builder()
                            .setMediaType(ActivityResultContracts.PickVisualMedia.ImageOnly)
                            .build()

                    galleryLauncher.launch(pickRequest)
                },
            )

            Spacer(modifier = Modifier.height(UiConfigs.Spacing.Small))

            // 拍照按钮
            ImagePickerOption(
                icon = Icons.Filled.CameraAlt,
                text = stringResource(R.string.image_picker_camera),
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
                        LogUtils.e(error.localizedMessage)
                        ToastUtils.showShort(error.localizedMessage.orEmpty())
                    }
                },
            )

            Spacer(modifier = Modifier.height(UiConfigs.Spacing.Medium))

            // 取消按钮
            ImagePickerOption(
                icon = null,
                text = stringResource(R.string.cancel),
                onClick = {
                    scope
                        .launch { sheetState.hide() }
                        .invokeOnCompletion {
                            if (!sheetState.isVisible) {
                                onDismiss()
                            }
                        }
                },
                isCancel = true,
            )

            Spacer(modifier = Modifier.height(UiConfigs.Padding.DialogContentVertical))
        }
    }
}

/**
 * 图片选择选项按钮
 *
 * @param icon 图标，如果为null则不显示图标
 * @param text 按钮文字
 * @param onClick 点击回调
 * @param isCancel 是否为取消按钮，取消按钮使用不同的样式
 */
@Composable
private fun ImagePickerOption(
    icon: androidx.compose.ui.graphics.vector.ImageVector?,
    text: String,
    onClick: () -> Unit,
    isCancel: Boolean = false,
) {
    Row(
        modifier =
            Modifier.fillMaxWidth()
                .clickable(onClick = onClick)
                .padding(
                    horizontal = UiConfigs.Padding.DialogContentHorizontal,
                    vertical = UiConfigs.Padding.DialogInner,
                ),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement =
            if (icon != null) {
                Arrangement.Start
            } else {
                Arrangement.Center
            },
    ) {
        if (icon != null) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                modifier = Modifier.size(24.dp),
                tint = if (isCancel) Color.Red else Color.White,
            )
            Spacer(modifier = Modifier.size(UiConfigs.Spacing.Small))
        }

        Text(
            text = text,
            fontSize = UiConfigs.Typography.Button,
            fontWeight = if (isCancel) FontWeight.Normal else FontWeight.Normal,
            color = if (isCancel) Color.Red else Color.White,
        )
    }
}
