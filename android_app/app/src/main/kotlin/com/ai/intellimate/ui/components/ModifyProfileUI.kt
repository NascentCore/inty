package com.ai.intellimate.ui.components

import ai.sxwl.android.data.api.model.GENDER
import ai.sxwl.android.data.api.model.UserProfile
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.design.ui.HeartPrimaryButton
import ai.sxwl.android.design.ui.HeartTopAppBar
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.ui.IntySmallTextField2
import com.ai.intellimate.ui.NameInputKeyBoardOption
import com.ai.intellimate.ui.SingleLineInputField
import com.ai.intellimate.xb.components.MultiLineBasicTextField

/** 编辑类型枚举 */
enum class EditKey {
    None,
    Name,
    Pronouns,
    Persona,
    Preference,
}

/** 编辑类型显示名称扩展 */
@Composable
private fun EditKey.toDisplayName(): String {
    return when (this) {
        EditKey.None -> ""
        EditKey.Name -> stringResource(R.string.str_name)
        EditKey.Pronouns -> stringResource(R.string.str_pronouns)
        EditKey.Preference -> stringResource(R.string.chat_settings_preference_title)
        EditKey.Persona -> stringResource(R.string.str_persona)
    }
}

/** 个人设置页面主界面 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileInfoScreen(
    userProfile: UserProfile,
    preference: String = "",
    isAppearanceUploading: Boolean = false,
    onBack: () -> Unit = {},
    onSelectAvatar: () -> Unit = {},
    onClickName: () -> Unit = {},
    onClickPronouns: () -> Unit = {},
    onClickPreference: () -> Unit = {},
    onClickPersona: () -> Unit = {},
    onClickAppearance: () -> Unit = {},
) {
    Scaffold(
        modifier = Modifier.background(HeartColor.primaryColor),
        containerColor = HeartColor.primaryColor,
        topBar = {
            HeartTopAppBar(
                modifier = Modifier.background(color = HeartColor.primaryColor),
                title = stringResource(R.string.str_edit_my_persona),
                navIcon = R.drawable.back,
                onBack = onBack,
            )
        },
    ) { innerPadding ->
        Column(
            modifier = Modifier.padding(innerPadding),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(Modifier.height(16.dp))

            // 头像区域
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                AvatarSection(avatar = userProfile.avatar ?: "", onSelectAvatar = onSelectAvatar)
            }

            Spacer(Modifier.height(46.dp))

            val horizontalPadding = 16

            // 设置项区域
            MyPersonaSettingsGroup(
                userProfile = userProfile,
                preference = preference,
                isAppearanceUploading = isAppearanceUploading,
                horizontalPadding = horizontalPadding,
                onClickName = onClickName,
                onClickPronouns = onClickPronouns,
                onClickPreference = onClickPreference,
                onClickPersona = onClickPersona,
                onClickAppearance = onClickAppearance,
            )

            Spacer(Modifier.weight(1f))

            Spacer(Modifier.height(60.dp))
        }
    }
}

/** 头像选择区域 */
@Composable
private fun AvatarSection(avatar: String, onSelectAvatar: () -> Unit) {
    Box(
        modifier =
            Modifier.size(120.dp)
                .background(color = Color.White, shape = CircleShape)
                .padding(4.dp),
        contentAlignment = Alignment.Center,
    ) {
        AsyncImage(
            modifier = Modifier.fillMaxSize().clip(CircleShape),
            model = ImageRequest.Builder(LocalContext.current).data(avatar).build(),
            placeholder = painterResource(R.drawable.app_icon),
            error = painterResource(R.drawable.app_icon),
            contentDescription = null,
        )
        Image(
            modifier =
                Modifier.size(40.dp).align(Alignment.BottomEnd).noRippleClickable {
                    onSelectAvatar()
                },
            painter = painterResource(R.drawable.icon_camera),
            contentDescription = null,
        )
    }
}

/** 编辑对话框组件 */
@Composable
fun EditDialog(
    editKey: EditKey,
    editValue: String,
    onDismiss: () -> Unit,
    onSave: (EditKey, String) -> Unit,
    onValueChange: (String) -> Unit,
) {
    Box(modifier = Modifier.imePadding().noRippleClickable { onDismiss() }) {
        Column(
            modifier =
                Modifier.align(Alignment.BottomCenter)
                    .fillMaxWidth()
                    .background(
                        brush =
                            Brush.verticalGradient(
                                colors = listOf(Color(0xff322341), Color(0xff120E24))
                            ),
                        shape = RoundedCornerShape(24.dp, 24.dp, 0.dp, 0.dp),
                    ),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // 关闭按钮
            Image(
                painter = painterResource(R.drawable.close),
                contentDescription = null,
                modifier =
                    Modifier.padding(16.dp).align(Alignment.End).noRippleClickable { onDismiss() },
            )

            // 标题
            val displayName = editKey.toDisplayName()
            Text(
                text = displayName,
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.SemiBold,
            )

            Spacer(Modifier.height(22.dp))

            // 编辑内容
            EditContent(editKey = editKey, editValue = editValue, onValueChange = onValueChange)

            Spacer(Modifier.height(40.dp))

            // 保存按钮
            HeartPrimaryButton(
                btnText = stringResource(R.string.save),
                onClick = { onSave(editKey, editValue) },
            )

            Spacer(Modifier.height(60.dp))
        }
    }
}

/** 编辑内容组件 */
@Composable
private fun EditContent(editKey: EditKey, editValue: String, onValueChange: (String) -> Unit) {
    when (editKey) {
        EditKey.Name -> {
            SingleLineInputField(
                value = editValue,
                onValueChange = onValueChange,
                keyboardOptions = NameInputKeyBoardOption,
            )
        }

        EditKey.Persona -> {
            Box(modifier = Modifier.padding(horizontal = 16.dp)) {
                MultiLineBasicTextField(
                    value = editValue,
                    onValueChange = onValueChange,
                    minLines = 3,
                    maxLength = 400,
                    placeholder = stringResource(R.string.please_enter_character_full),
                    backgroundColor = Color.White.copy(0.1f),
                )
            }
        }

        EditKey.Pronouns -> {
            PronounsEditField(value = editValue, onValueChange = onValueChange)
        }

        EditKey.Preference -> {
            SingleLineInputField(
                value = editValue,
                onValueChange = onValueChange,
                placeholder = stringResource(R.string.chat_settings_preference_hint),
                keyboardOptions =
                    KeyboardOptions(
                        imeAction = ImeAction.Done,
                        capitalization = KeyboardCapitalization.None,
                    ),
            )
        }

        EditKey.None -> {
            // 空内容
        }
    }
}

/** 角色描述编辑字段 */
@Composable
private fun PersonaEditField(value: String, onValueChange: (String) -> Unit) {
    val focusRequester = remember { FocusRequester() }
    Box(
        modifier =
            Modifier.padding(horizontal = 16.dp, vertical = 0.dp)
                .fillMaxWidth()
                .height(112.dp)
                .background(Color.White.copy(0.1f), RoundedCornerShape(8.dp))
                .border(
                    width = 0.5.dp,
                    color = Color.White.copy(0.2f),
                    shape = RoundedCornerShape(8.dp),
                )
                .clickable { focusRequester.requestFocus() }
    ) {
        IntySmallTextField2(
            modifier = Modifier.fillMaxSize().focusRequester(focusRequester),
            value = value,
            onValueChange = onValueChange,
            maxLength = 400,
            singleLine = false,
            placeholder = {
                Text(
                    text = stringResource(R.string.please_enter_character_full),
                    color = Color.White.copy(0.55f),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Normal,
                )
            },
        )
        Text(
            modifier = Modifier.align(Alignment.BottomEnd).padding(12.dp, 8.dp),
            text = stringResource(R.string.character_count_format_my, value.length),
            color = Color.White.copy(0.55f),
            fontSize = 12.sp,
            fontWeight = FontWeight.Normal,
        )
    }
}

/** 代词选择编辑字段 */
@Composable
private fun PronounsEditField(value: String, onValueChange: (String) -> Unit) {
    Row(
        modifier =
            Modifier.padding(horizontal = 16.dp, vertical = 0.dp).fillMaxWidth().height(48.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        PronounsItem(
            text = stringResource(R.string.he_him),
            isSelected = (value == GENDER.MALE.value),
            onSelected = { onValueChange(GENDER.MALE.value) },
        )
        Spacer(Modifier.width(6.dp))
        PronounsItem(
            text = stringResource(R.string.she_her),
            isSelected = (value == GENDER.FEMALE.value),
            onSelected = { onValueChange(GENDER.FEMALE.value) },
        )
        Spacer(Modifier.width(6.dp))
        PronounsItem(
            text = stringResource(R.string.they_them),
            isSelected = (value != GENDER.MALE.value && value != GENDER.FEMALE.value),
            onSelected = { onValueChange(GENDER.OTHER.value) },
        )
    }
}

/** 代词选择项组件 */
@Composable
private fun RowScope.PronounsItem(
    text: String,
    isSelected: Boolean = false,
    onSelected: () -> Unit = {},
) {
    Box(
        modifier =
            Modifier.weight(1f)
                .fillMaxHeight()
                .background(color = Color(0x3378599A), shape = RoundedCornerShape(24.dp))
                .then(
                    if (isSelected) {
                        Modifier.border(
                            brush =
                                Brush.linearGradient(
                                    colors = listOf(Color(0xffC122FF), Color(0xffFF905D))
                                ),
                            width = 2.dp,
                            shape = RoundedCornerShape(24.dp),
                        )
                    } else {
                        Modifier.border(
                            width = 0.5.dp,
                            color = Color.White.copy(0.2f),
                            shape = RoundedCornerShape(24.dp),
                        )
                    }
                )
                .noRippleClickable { onSelected() },
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

@Preview(showBackground = true, backgroundColor = 0xff000000)
@Composable
private fun ProfileInfoScreenPreview() {
    ProfileInfoScreen(userProfile = UserProfile(nickname = "nick", id = "12345", avatar = ""))
}
