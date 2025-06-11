package com.ai.inty

import android.app.Activity
import android.os.Bundle
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntySmallTextField
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.GENDER
import com.ai.inty.beans.UserProfile
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.utils.UCropHelper
import com.ai.inty.viewmodels.MySettingActivityViewModel
import com.inty.utils.log.EasyLog
import com.therouter.router.Autowired
import com.therouter.router.Route
import com.yalantis.ucrop.UCrop
import kotlinx.coroutines.launch


enum class EditKey {
    None,
    Name,
    Pronouns,
    Persona
}

fun EditKey.toDisplayName(): String {
    when (this) {
        EditKey.None -> return ""
        EditKey.Name -> return "Name"
        EditKey.Pronouns -> return "My Pronouns"
        EditKey.Persona -> return "My Persona"
    }
}

@Route(path = Constant.ROUTE_SETTING_MY)
class MySettingActivity: BaseActivity() {

    @Autowired
    var userProfile: UserProfile? = null

    private val viewModel = MySettingActivityViewModel()

    @OptIn(ExperimentalMaterial3Api::class)
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

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
                    if (it.resultCode == Activity.RESULT_OK) {
                        it.data?.let { intentResult ->
                            val imageUri = UCrop.getOutput(intentResult) // 图片uri
                            imageUri?.let { imageUriReal ->
                                viewModel.setAvatar(imageUriReal)
                            }
                            EasyLog.log("select $imageUri")
                        }
                    }
                }

                val galleryLauncher = rememberLauncherForActivityResult(
                    ActivityResultContracts.GetContent()) { imageUri ->
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
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(Color.Black.copy(0.6f))
                                .noRippleClickable {
                                    editKey = EditKey.None
                                }
                            ,
                        ) {


                            Column(
                                modifier = Modifier
                                    .align(Alignment.BottomCenter)
                                    .fillMaxWidth()
                                    .background(
                                        brush = Brush.verticalGradient(
                                            colors = listOf(Color(0xff322341), Color(0xff120E24))
                                        ),
                                        shape = RoundedCornerShape(24.dp, 24.dp, 0.dp, 0.dp)
                                    ),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Image(
                                    painter = painterResource(R.drawable.close),
                                    contentDescription = null,
                                    modifier = Modifier
                                        .padding(16.dp)
                                        .align(Alignment.End)
                                        .noRippleClickable {
                                            editKey = EditKey.None
                                        }
                                )

                                Text(
                                    text = editKey.toDisplayName(),
                                    color = Color.White,
                                    fontSize = 20.sp,
                                    fontWeight = FontWeight.SemiBold,
                                )

                                Spacer(Modifier.height(22.dp))

                                when (editKey) {
                                    EditKey.Name -> {
                                        Row(
                                            modifier = Modifier
                                                .padding(horizontal = 16.dp, vertical = 0.dp)
                                                .fillMaxWidth().height(48.dp)
                                                .background(
                                                    Color.White.copy(0.1f),
                                                    RoundedCornerShape(8.dp)
                                                )
                                                .border(
                                                    width = 0.5.dp,
                                                    color = Color.White.copy(0.2f),
                                                    shape = RoundedCornerShape(8.dp)
                                                ),
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            IntySmallTextField(
                                                modifier = Modifier.weight(1f),
                                                value = editValue,
                                                onValueChange = {
                                                    editValue = it
                                                },
                                            )
                                        }
                                    }

                                    EditKey.Persona -> {
                                        Box(
                                            modifier = Modifier
                                                .padding(horizontal = 16.dp, vertical = 0.dp)
                                                .fillMaxWidth().height(112.dp)
                                                .background(
                                                    Color.White.copy(0.1f),
                                                    RoundedCornerShape(8.dp)
                                                )
                                                .border(
                                                    width = 0.5.dp,
                                                    color = Color.White.copy(0.2f),
                                                    shape = RoundedCornerShape(8.dp)
                                                ),
                                        ) {
                                            IntySmallTextField(
                                                modifier = Modifier.fillMaxSize(),
                                                value = editValue,
                                                onValueChange = {
                                                    editValue = it
                                                },
                                                placeholder = {
                                                    Text(
                                                        modifier = Modifier
                                                            .padding(16.dp, 12.dp),
                                                        text = "Please enter your character...",
                                                        color = Color.White.copy(0.55f),
                                                        fontSize = 12.sp,
                                                        fontWeight = FontWeight.Normal,
                                                    )
                                                }
                                            )
                                            Text(
                                                modifier = Modifier.align(Alignment.BottomEnd)
                                                    .padding(12.dp, 8.dp),
                                                text = "${editValue.length}/400",
                                                color = Color.White.copy(0.55f),
                                                fontSize = 12.sp,
                                                fontWeight = FontWeight.Normal,
                                            )
                                        }
                                    }

                                    EditKey.Pronouns -> {
                                        Row(
                                            modifier = Modifier
                                                .padding(horizontal = 16.dp, vertical = 0.dp)
                                                .fillMaxWidth().height(48.dp)
//                                                .background(
//                                                    Color.White.copy(0.1f),
//                                                    RoundedCornerShape(8.dp)
//                                                )
//                                                .border(
//                                                    width = 0.5.dp,
//                                                    color = Color.White.copy(0.2f),
//                                                    shape = RoundedCornerShape(8.dp)
//                                                )
                                            ,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            PronounsItem(
                                                text = "He/Him",
                                                isSelected = (editValue == GENDER.MALE.value),
                                                onSelected = {
                                                    editValue = GENDER.MALE.value
                                                }
                                            )
                                            Spacer(Modifier.width(6.dp))
                                            PronounsItem(
                                                text = "She/Her",
                                                isSelected = (editValue == GENDER.FEMALE.value),
                                                onSelected = {
                                                    editValue = GENDER.FEMALE.value
                                                }
                                            )
                                            Spacer(Modifier.width(6.dp))
                                            PronounsItem(
                                                text = "They/Them",
                                                isSelected = (editValue != GENDER.MALE.value && editValue != GENDER.FEMALE.value),
                                                onSelected = {
                                                    editValue = GENDER.OTHER.value
                                                }
                                            )
                                        }
                                    }

                                    EditKey.None -> {

                                    }
                                }

                                Spacer(Modifier.height(40.dp))

                                SaveBtn(onSave = {
                                    viewModel.changeUserProfile(editKey, editValue)
                                    editKey = EditKey.None
                                })

                                Spacer(Modifier.height(60.dp))
                            }
                        }
                    }
                }

            }
        }
    }
}


@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MySettingScreen(
    userProfile: UserProfile,
    onBack: () -> Unit = {},
    onSelectAvatar: () -> Unit = {},
    onClickName: () -> Unit = {},
    onClickPronouns: () -> Unit = {},
    onClickPersona: () -> Unit = {},
    onSave: () -> Unit = {}
) {
    Scaffold(
        modifier = Modifier.background(BackGround),
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.settings),
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 20.sp,
                    )
                },
                navigationIcon = {
                    Image(
                        modifier = Modifier
                            .padding(horizontal = 12.dp)
                            .noRippleClickable {
                                onBack()
                            },
                        painter = painterResource(R.drawable.back),
                        contentDescription = null,
                    )

                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier.padding(innerPadding)
        ) {
            Spacer(Modifier.height(16.dp))

            Box(
                modifier = Modifier
                    .size(120.dp)
                    .background(color = Color.White, shape = CircleShape)
                    .padding(4.dp)
                    .align(Alignment.CenterHorizontally)
            ) {
                IntyCircleImage(
                    modifier = Modifier.fillMaxSize(),
                    url = userProfile.avatar,
                    placeholderResID = R.drawable.ic_launcher_background
                )
                Image(
                    modifier = Modifier
                        .size(40.dp)
                        .align(Alignment.BottomEnd)
                        .noRippleClickable {
                            onSelectAvatar()
                        },
                    painter = painterResource(R.drawable.icon_camera),
                    contentDescription = null,
                )
            }

            Spacer(Modifier.height(46.dp))

            Column(
                modifier = Modifier
                    .padding(horizontal = 16.dp)
                    .fillMaxWidth()
                    .border(
                        brush = Brush.linearGradient(
                            colors = listOf(
                                Color.Transparent,
                                Color.White.copy(0.2f),
                                Color.Transparent
                            )
                        ),
                        width = 1.dp,
                        shape = RoundedCornerShape(8.dp)
                    )
                    .background(
                        color = Color(0x3378599A),
                        shape = RoundedCornerShape(8.dp)
                    )
            ) {
                Spacer(Modifier.height(8.dp))

                MySettingItem(
                    key = "Name",
                    value = userProfile.nickname,
                    onClick = onClickName
                )
                SpacerLine()
                MySettingItem(
                    key = "My Pronouns",
                    value = userProfile.gender ?: "",
                    onClick = onClickPronouns
                )
                SpacerLine()
                MySettingItem(
                    key = "My Persona",
                    value = userProfile.description ?: "",
                    onClick = onClickPersona
                )

                Spacer(Modifier.height(8.dp))
            }

            Spacer(Modifier.weight(1f))

            SaveBtn(onSave)

            Spacer(Modifier.height(60.dp))
        }
    }
}

@Composable
private fun SaveBtn(onSave: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .height(50.dp)
            .background(
                brush = Brush.linearGradient(
                    colors = listOf(Color(0xFFC122FF), Color(0xFFFF905D))
                ),
                shape = RoundedCornerShape(25.dp)
            )
            .noRippleClickable {
                onSave()
            }
    ) {
        Text(
            modifier = Modifier.align(Alignment.Center),
            text = "Save",
            fontSize = 16.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White,
        )
    }
}

@Composable
private fun MySettingItem(
    key: String,
    value: String,
    onClick: () -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
            .padding(horizontal = 12.dp)
            .noRippleClickable {
                onClick()
            },
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = key,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White

        )
        Spacer(Modifier.weight(1f))
        Text(
            text = value,
            fontSize = 14.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White.copy(0.55f)

        )
        Spacer(Modifier.width(10.dp))
        Image(
            painter = painterResource(R.drawable.icon_next),
            contentDescription = null,
        )
    }
}

@Composable
private fun SpacerLine() {
    Spacer(Modifier.height(4.dp))
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(
                brush = Brush.horizontalGradient(
                    colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                )
            )
    ) {}
    Spacer(Modifier.height(4.dp))
}


@Composable
@Preview(showBackground = true, backgroundColor = 0xff000000)
fun MySettingScreenPreview(

) {
    MySettingScreen(
        userProfile = UserProfile(
            nickname = "nick",
            id = "12345",
            avatar = ""
        )
    )
}

@Composable
fun RowScope.PronounsItem(
    text: String,
    isSelected: Boolean = false,
    onSelected: () -> Unit = {}
) {
    Box(
        modifier = Modifier
            .weight(1f)
            .fillMaxHeight()
            .background(
                color = Color(0x3378599A),
                shape = RoundedCornerShape(24.dp)
            )
            .then(
                if (isSelected) {
                    Modifier.border(
                        brush = Brush.linearGradient(
                            colors = listOf(
                                Color(0xffC122FF),
                                Color(0xffFF905D),
                            )
                        ),
                        width = 2.dp,
                        shape = RoundedCornerShape(24.dp)
                    )
                } else {
                    Modifier.border(
                        width = 0.5.dp,
                        color = Color.White.copy(0.2f),
                        shape = RoundedCornerShape(24.dp)
                    )
                }
            )
            .noRippleClickable {
                onSelected()
            }
        ,
        contentAlignment = Alignment.Center,
    ) {
        if (isSelected) {
            Text(
                text = text,
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
            )
        } else {
            Text(
                text = text,
                color = Color.White.copy(0.55f),
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
            )
        }
    }
}