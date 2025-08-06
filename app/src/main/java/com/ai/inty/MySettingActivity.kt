package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.ui.components.EditDialog
import com.ai.inty.ui.components.EditKey
import com.ai.inty.ui.components.MySettingScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.utils.UCropHelper
import com.ai.inty.viewmodels.MySettingActivityViewModel
import com.inty.utils.log.EasyLog
import com.therouter.router.Autowired
import com.therouter.router.Route
import com.yalantis.ucrop.UCrop
import kotlinx.coroutines.launch


/**
 * 个人设置页面
 */
@Route(path = Constant.ROUTE_SETTING_MY)
class MySettingActivity : BaseActivity() {

    @Autowired
    var userProfile: com.ai.inty.beans.UserProfile? = null

    private val viewModel = MySettingActivityViewModel()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        viewModel.init(userProfile)

        lifecycleScope.launch {
            viewModel.finishActivity.collect {
                if (it) {
                    finish()
                }
            }
        }

        setContent {
            IntyTheme {
                val context = LocalContext.current
                val cropTitle = stringResource(id = R.string.crop_image)

                val activityCropResultLauncher = rememberLauncherForActivityResult(
                    ActivityResultContracts.StartActivityForResult()
                ) {
                    if (it.resultCode == RESULT_OK) {
                        it.data?.let { intentResult ->
                            val imageUri = UCrop.getOutput(intentResult)
                            imageUri?.let { imageUriReal ->
                                viewModel.setAvatar(imageUriReal)
                            }
                            EasyLog.log("select $imageUri")
                        }
                    }
                }

                val galleryLauncher = rememberLauncherForActivityResult(
                    ActivityResultContracts.GetContent()
                ) { imageUri ->
                    imageUri?.let {
                        val intentCrop = UCropHelper.getIntent(context, it, cropTitle)
                        activityCropResultLauncher.launch(intentCrop)
                    }
                }

                val userProfile = viewModel.userProfile.collectAsState()
                var editKey by remember { mutableStateOf(EditKey.None) }
                var editValue by rememberSaveable { mutableStateOf("") }

                Box {
                    MySettingScreen(
                        userProfile = userProfile.value,
                        onBack = {
                            finish()
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
                        onSelectAvatar = {
                            galleryLauncher.launch("image/*")
                        },
                        onSave = {
                            viewModel.onSave()
                        }
                    )

                    if (editKey != EditKey.None) {
                        EditDialog(
                            editKey = editKey,
                            editValue = editValue,
                            onDismiss = {
                                editKey = EditKey.None
                            },
                            onSave = { key, value ->
                                viewModel.changeUserProfile(key, value)
                                editKey = EditKey.None
                            },
                            onValueChange = {
                                editValue = it
                            }
                        )
                    }
                }
            }
        }
    }
}
