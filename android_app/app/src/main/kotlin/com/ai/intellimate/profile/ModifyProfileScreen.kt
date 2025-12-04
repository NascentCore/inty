package com.ai.intellimate.profile

import ai.sxwl.android.utils.ToastUtils
import android.app.Activity.RESULT_OK
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.EditDialog
import com.ai.intellimate.ui.components.EditKey
import com.ai.intellimate.ui.components.ProfileInfoScreen
import com.ai.intellimate.utils.UCropHelper
import com.yalantis.ucrop.UCrop
import kotlinx.coroutines.launch
import java.util.Locale

@Composable
internal fun ModifyProfileScreen(
    navController: NavController,
    viewModel: ModifyProfileViewModel = viewModel()
) {
//    val context = LocalContext.current
    val cropTitle = stringResource(id = R.string.crop_image)

//    val activityCropResultLauncher =
//        rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) {
//                result ->
//            if (result.resultCode == RESULT_OK) {
//                runCatching {
//                    result.data?.let { intentResult ->
//                        val imageUri = UCrop.getOutput(intentResult) // 图片uri
//                        imageUri?.let { imageUriReal -> viewModel.setAvatar(imageUriReal) }
//                    }
//                }
//                    .onFailure { e -> e.printStackTrace() }
//            }
//        }
//
//    val galleryLauncher =
//        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
//            imageUri?.let { uri ->
//                runCatching {
//                    // Check file size before cropping - limit to 10MB
//                    val fileSize = getFileSize(context, uri)
//                    // TODO: 使用 firebase remote config 配置应集中管理
//                    // https://firebase.google.com/docs/remote-config
//                    val maxSizeMB = 10
//                    val maxSizeBytes = maxSizeMB * 1024 * 1024 // 10MB in bytes
//                    if (fileSize > maxSizeBytes) {
//                        val maxSizeMBStr =
//                            String.Companion.format(Locale.getDefault(), "%dMB", maxSizeMB)
//                        val fileSizeMBStr =
//                            String.Companion.format(
//                                Locale.getDefault(),
//                                "%.1fMB",
//                                fileSize / (1024.0 * 1024.0),
//                            )
//                        val msg =
//                            String.format(
//                                context.getString(
//                                    R.string.user_avatar_size_too_large_with_size_format
//                                ),
//                                maxSizeMBStr,
//                                fileSizeMBStr,
//                            )
//                        lifecycleScope.launch { ToastUtils.showShort(msg) }
//                        return@let
//                    }
//                    val intentCrop = UCropHelper.getIntent(context, uri, cropTitle)
//                    activityCropResultLauncher.launch(intentCrop)
//                }
//                    .onFailure { it.printStackTrace() }
//            }
//        }

    val userProfile = viewModel.userProfile.collectAsState()
    val isSaving = viewModel.isSaving.collectAsState()
    var editKey by remember { mutableStateOf(EditKey.None) }
    var editValue by rememberSaveable { mutableStateOf("") }

    Box {
        ProfileInfoScreen(
            userProfile = userProfile.value,
            onBack = {
                navController.popBackStack()
            },
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
            onSelectAvatar = {  },
            onSave = { viewModel.onSave() },
            isSaving = isSaving.value,
        )

        if (editKey != EditKey.None) {
            EditDialog(
                editKey = editKey,
                editValue = editValue,
                onDismiss = { editKey = EditKey.None },
                onSave = { key, value ->
                    // 在各自的 sheet 中点击 save 时，立即调用接口更新
                    // updateFieldAndSave 会判断是否变化，并更新本地状态
                    viewModel.updateFieldAndSave(key, value)
                    editKey = EditKey.None
                },
                onValueChange = { editValue = it },
            )
        }
    }
}