package com.ai.intellimate.profile

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.design.ui.HeartTopAppBar
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import com.ai.intellimate.utils.NetworkErrorHandler
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.compose.composable
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import java.io.File
import kotlinx.serialization.Serializable

@Serializable private data object UploadSelfie

fun NavController.toUploadSelfie() {
    navigate(UploadSelfie)
}

fun NavGraphBuilder.uploadSelfieScreen(onBack: () -> Unit) {
    composable<UploadSelfie> { UploadSelfieScreen(onBack = onBack) }
}

@Composable
fun UploadSelfieScreen(onBack: () -> Unit, viewModel: ModifyProfileViewModel = viewModel()) {
    val context = LocalContext.current
    val userProfile by viewModel.userProfile.collectAsState()
    val isAppearanceUploading by viewModel.isAppearanceUploading.collectAsState()
    // 创建临时文件用于拍照
    var tempTakePic by remember { mutableStateOf<Uri?>(null) }

    // 相册选择器
    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
            uri?.let { viewModel.setUserAppearance(it) }
        }

    // 相机拍照
    val cameraLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
            if (success) {
                tempTakePic?.let { viewModel.setUserAppearance(it) }
            }
        }

    UploadSelfieScreen(
        image = getCdnImageUrl(userProfile.userPhoto),
        isLoading = isAppearanceUploading,
        onChoosePhoto = {
            val pickRequest =
                PickVisualMediaRequest.Builder()
                    .setMediaType(ActivityResultContracts.PickVisualMedia.ImageOnly)
                    .build()

            galleryLauncher.launch(pickRequest)
        },
        onTakeSelfie = {
            try {
                val file =
                    File.createTempFile("${System.currentTimeMillis()}", ".jpg", context.cacheDir)
                tempTakePic =
                    FileProvider.getUriForFile(context, "${context.packageName}.provider", file)
                        .also { cameraLauncher.launch(it) }
            } catch (error: Throwable) {
                // #region agent log
                val msg = error.localizedMessage.orEmpty()
                NetworkErrorHandler.writeTlsParseDebugLogIfRelevant("F", "UploadSelfieScreen.kt:onTakeSelfie", msg)
                // #endregion
                LogUtils.e(error.localizedMessage)
                ToastUtils.showShort(msg)
            }
        },
        onBack = onBack,
    )
}

@Composable
fun UploadSelfieScreen(
    image: String?,
    isLoading: Boolean,
    onChoosePhoto: () -> Unit,
    onTakeSelfie: () -> Unit,
    onBack: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Scaffold(
        topBar = {
            HeartTopAppBar(
                modifier = Modifier.background(color = MaterialTheme.colorScheme.background),
                title = stringResource(R.string.str_appearance),
                navIcon = R.drawable.back,
                onBack = onBack,
            )
        },
        containerColor = MaterialTheme.colorScheme.background,
        modifier = modifier,
    ) { contentPadding ->
        Column(
            modifier =
                modifier
                    .fillMaxSize()
                    .padding(contentPadding)
                    .padding(horizontal = UiConfigs.Padding.ScreenHorizontal),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // 1. 显示已上传的照片（如果有）
            Box(modifier = Modifier.fillMaxWidth().height(300.dp).clip(RoundedCornerShape(16.dp))) {
                AsyncImage(
                    model = image,
                    contentDescription = stringResource(R.string.str_appearance),
                    modifier = Modifier.fillMaxSize(),
                    contentScale = ContentScale.Fit,
                )
            }
            Spacer(modifier = Modifier.height(UiConfigs.Spacing.XLarge))

            // 2. 功能解释文案
            Text(
                text = stringResource(R.string.image_pick_protagonist_title),
                style = MaterialTheme.typography.titleLarge,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onBackground,
            )
            Spacer(modifier = Modifier.height(UiConfigs.Spacing.Medium))
            Text(
                text = stringResource(R.string.image_pick_reference_description),
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f),
            )
            Spacer(modifier = Modifier.height(5.dp))
            Text(
                text = stringResource(R.string.upload_selfie_tips),
                style = MaterialTheme.typography.bodyMedium,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f),
            )
            Spacer(modifier = Modifier.height(UiConfigs.Spacing.XLarge))
            AnimatedContent(targetState = isLoading, contentAlignment = Alignment.Center) {
                if (it) {
                    CircularProgressIndicator()
                } else {
                    Column() {
                        // 3. 两个可点击按钮
                        Button(
                            onClick = onChoosePhoto,
                            modifier = Modifier.fillMaxWidth(),
                            colors =
                                ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.primary
                                ),
                            shape = RoundedCornerShape(UiConfigs.Shape.PrimaryButton),
                        ) {
                            Text(
                                text = stringResource(R.string.image_picker_gallery),
                                fontSize = UiConfigs.Typography.Button,
                                style = MaterialTheme.typography.labelLarge,
                            )
                        }
                        Spacer(modifier = Modifier.height(UiConfigs.Spacing.Medium))
                        Button(
                            onClick = onTakeSelfie,
                            modifier = Modifier.fillMaxWidth(),
                            colors =
                                ButtonDefaults.buttonColors(
                                    containerColor = MaterialTheme.colorScheme.primary,
                                    contentColor = Color.White,
                                ),
                            shape = RoundedCornerShape(UiConfigs.Shape.PrimaryButton),
                        ) {
                            Text(
                                text = stringResource(R.string.image_picker_camera),
                                fontSize = UiConfigs.Typography.Button,
                                style = MaterialTheme.typography.labelLarge,
                            )
                        }
                    }
                }
            }
        }
    }
}

@Preview(showSystemUi = true, showBackground = false)
@Composable
private fun UploadSelfieScreenPreview() {
    IntelliMateTheme {
        UploadSelfieScreen(
            image = "dasd",
            isLoading = false,
            onChoosePhoto = {},
            onTakeSelfie = {},
            onBack = {},
        )
    }
}
