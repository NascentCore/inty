package com.ai.intellimate.profile

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.utils.ToastUtils
import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
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
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.EditDialog
import com.ai.intellimate.ui.components.EditKey
import com.ai.intellimate.ui.components.MySettingScreen
import com.ai.intellimate.utils.UCropHelper
import com.ai.intellimate.ViewModelEvent
import com.yalantis.ucrop.UCrop
import kotlinx.coroutines.launch
import java.util.Locale

/** 个人设置页面 */
class ModifyProfileActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_USER_INFO = "intent_key_agent_info"

        /**
         * 启动单独的聊天界面
         * @param context 上下文context
         * @param userInfo UserProfile对象
         */
        fun launch(context: Context, userInfo: UserProfile? = null) {
            context.startActivity(
                Intent(
                    context,
                    ModifyProfileActivity::class.java
                ).also { intent ->
                intent.putExtra(INTENT_KEY_USER_INFO, userInfo)
            })
        }
    }

    private val viewModel: MySettingViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        val userProfile: UserProfile? = intent.getParcelableExtra(INTENT_KEY_USER_INFO)
        viewModel.init(userProfile)

        // 监听ViewModel事件
        lifecycleScope.launch {
            viewModel.events.collect { event ->
                when (event) {
                    is ViewModelEvent.UserProfileUpdated -> {
                        finish()
                    }

                    else -> {
                        // 其他事件暂不处理
                    }
                }
            }
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        val context = LocalContext.current
        val cropTitle = stringResource(id = R.string.crop_image)

        val activityCropResultLauncher =
            rememberLauncherForActivityResult(
                ActivityResultContracts.StartActivityForResult()
            ) { result ->
                if (result.resultCode == RESULT_OK) {
                    runCatching {
                        result.data?.let { intentResult ->
                            val imageUri = UCrop.getOutput(intentResult) // 图片uri
                            imageUri?.let { imageUriReal ->
                                viewModel.setAvatar(imageUriReal)
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
                                    fileSize / (1024.0 * 1024.0)
                                )
                            val msg =
                                String.format(
                                    context.getString(
                                        R.string
                                            .user_avatar_size_too_large_with_size_format
                                    ),
                                    maxSizeMBStr,
                                    fileSizeMBStr,
                                )
                            lifecycleScope.launch { ToastUtils.showShort(msg) }
                            return@let
                        }
                        val intentCrop = UCropHelper.getIntent(context, uri, cropTitle)
                        activityCropResultLauncher.launch(intentCrop)
                    }
                        .onFailure { it.printStackTrace() }
                }
            }

        val userProfile = viewModel.userProfile.collectAsState()
        val isSaving = viewModel.isSaving.collectAsState()
        var editKey by remember { mutableStateOf(EditKey.None) }
        var editValue by rememberSaveable { mutableStateOf("") }

        Box {
            MySettingScreen(
                userProfile = userProfile.value,
                onBack = { finish() },
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
                onSelectAvatar = { galleryLauncher.launch("image/*") },
                onSave = { viewModel.onSave() },
                isSaving = isSaving.value,
            )

            if (editKey != EditKey.None) {
                EditDialog(
                    editKey = editKey,
                    editValue = editValue,
                    onDismiss = { editKey = EditKey.None },
                    onSave = { key, value ->
                        viewModel.changeUserProfile(key, value)
                        editKey = EditKey.None
                    },
                    onValueChange = { editValue = it },
                )
            }
        }
    }

    private fun getFileSize(context: Context, uri: Uri): Long {
        return try {
            context.contentResolver.openInputStream(uri)?.use { input ->
                input.available().toLong()
            } ?: 0L
        } catch (e: Exception) {
            0L
        }
    }
}
