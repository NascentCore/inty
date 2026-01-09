package com.ai.intellimate.profile

import ai.sxwl.android.data.store.PersonaPreferenceStore
import ai.sxwl.android.utils.ToastUtils
import android.app.Activity.RESULT_OK
import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.EditDialog
import com.ai.intellimate.ui.components.EditKey
import com.ai.intellimate.ui.components.ImagePickerBottomSheet
import com.ai.intellimate.ui.components.ProfileInfoScreen
import com.ai.intellimate.utils.UCropHelper
import com.ai.intellimate.xb.helper.UserProfileStore
import com.yalantis.ucrop.UCrop
import java.util.Locale
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun ModifyProfileScreen(
    navController: NavController,
    viewModel: ModifyProfileViewModel = viewModel(),
) {
    val profile = UserProfileStore.getUserProfile()
    LaunchedEffect(profile?.id) { viewModel.init(profile) }

    val context = LocalContext.current
    val cropTitle = stringResource(id = R.string.crop_image)
    val scope = rememberCoroutineScope()

    val activityCropResultLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result
            ->
            if (result.resultCode == RESULT_OK) {
                runCatching {
                        result.data?.let { intentResult ->
                            val imageUri = UCrop.getOutput(intentResult) // 图片uri
                            imageUri?.let { imageUriReal ->
                                // 设置头像并立即保存（调用 onSave 方法）
                                viewModel.setAvatar(imageUriReal)
                                viewModel.onSave()
                            }
                        }
                    }
                    .onFailure { e -> e.printStackTrace() }
            }
        }

    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
            imageUri?.let { uri ->
                runCatching {
                        // Check file size before cropping - limit to 10MB
                        val fileSize = getFileSize(context, uri)
                        // TODO: 使用 firebase remote config 配置应集中管理
                        // https://firebase.google.com/docs/remote-config
                        val maxSizeMB = 10
                        val maxSizeBytes = maxSizeMB * 1024 * 1024 // 10MB in bytes
                        if (fileSize > maxSizeBytes) {
                            val maxSizeMBStr =
                                String.Companion.format(Locale.getDefault(), "%dMB", maxSizeMB)
                            val fileSizeMBStr =
                                String.Companion.format(
                                    Locale.getDefault(),
                                    "%.1fMB",
                                    fileSize / (1024.0 * 1024.0),
                                )
                            val msg =
                                String.format(
                                    context.getString(
                                        R.string.user_avatar_size_too_large_with_size_format
                                    ),
                                    maxSizeMBStr,
                                    fileSizeMBStr,
                                )
                            scope.launch { ToastUtils.showShort(msg) }
                            return@let
                        }
                        val intentCrop = UCropHelper.getIntent(context, uri, cropTitle)
                        activityCropResultLauncher.launch(intentCrop)
                    }
                    .onFailure { it.printStackTrace() }
            }
        }

    val userProfile = viewModel.userProfile.collectAsState()
    var editKey by remember { mutableStateOf(EditKey.None) }
    var editValue by rememberSaveable { mutableStateOf("") }

    val sheetState = rememberModalBottomSheetState(true)
    val isSaving by viewModel.isSaving.collectAsState()
    val preferenceFlow = remember(context) { PersonaPreferenceStore.preferenceFlow(context) }
    val userPreference by preferenceFlow.collectAsState(initial = "")
    var showImagePicker by remember { mutableStateOf(false) }
    val isAppearanceUploading by viewModel.isAppearanceUploading.collectAsState()

    //    LaunchedEffect(Unit) {
    //        viewModel.events.collect { event ->
    //            when (event) {
    //                is ViewModelEvent.UserProfileUpdated -> {
    //                    // todo
    //                }
    //                else -> {
    //                    // 其他事件暂不处理
    //                }
    //            }
    //        }
    //    }

    Box(modifier = Modifier.fillMaxSize()) {
        ProfileInfoScreen(
            userProfile = userProfile.value,
            preference = userPreference,
            isAppearanceUploading = isAppearanceUploading,
            onBack = { navController.popBackStack() },
            onClickName = {
                editKey = EditKey.Name
                editValue = userProfile.value.nickname
            },
            onClickPersona = {
                editKey = EditKey.Persona
                editValue = userProfile.value.description ?: ""
            },
            onClickPronouns = {
                editKey = EditKey.Pronouns
                editValue = userProfile.value.gender ?: ""
            },
            onClickPreference = {
                editKey = EditKey.Preference
                editValue = userPreference
            },
            onSelectAvatar = { galleryLauncher.launch("image/*") },
            onClickAppearance = { showImagePicker = true },
        )

        if (showImagePicker) {
            ImagePickerBottomSheet(
                onDismiss = { showImagePicker = false },
                onImageSelected = {
                    showImagePicker = false

                    viewModel.setUserAppearance(it)
                },
            )
        }

        if (editKey != EditKey.None) {
            ModalBottomSheet(
                onDismissRequest = { editKey = EditKey.None },
                sheetState = sheetState,
                dragHandle = null,
                contentWindowInsets = { WindowInsets() },
            ) {
                EditDialog(
                    editKey = editKey,
                    editValue = editValue,
                    onDismiss = {
                        scope
                            .launch { sheetState.hide() }
                            .invokeOnCompletion {
                                if (!sheetState.isVisible) {
                                    editKey = EditKey.None
                                }
                            }
                    },
                    onSave = { key, value ->
                        // 在各自的 sheet 中点击 save 时，立即调用接口更新
                        // updateFieldAndSave 会判断是否变化，并更新本地状态
                        if (key == EditKey.Preference) {
                            scope.launch {
                                PersonaPreferenceStore.savePreference(context, value.trim())
                            }
                        } else {
                            viewModel.updateFieldAndSave(key, value)
                        }

                        scope
                            .launch { sheetState.hide() }
                            .invokeOnCompletion {
                                if (!sheetState.isVisible) {
                                    editKey = EditKey.None
                                }
                            }
                    },
                    onValueChange = { editValue = it },
                )
            }
        }

        if (isSaving) {
            Box(
                modifier = Modifier.fillMaxSize().background(Color.Black.copy(alpha = 0.55f)),
                contentAlignment = Alignment.Center,
            ) {
                CircularProgressIndicator(color = Color.White, modifier = Modifier.size(32.dp))
            }
        }
    }
}

private fun getFileSize(context: Context, uri: Uri): Long {
    return try {
        context.contentResolver.openInputStream(uri)?.use { input -> input.available().toLong() }
            ?: 0L
    } catch (e: Exception) {
        0L
    }
}
