package com.ai.inty.ui.components

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.inty.R
import com.ai.inty.base.IntySmallTextField
import com.ai.inty.base.IntySmallTextField2
import com.ai.inty.beans.GENDER
import com.ai.inty.beans.UserProfile

/** 编辑类型枚举 */
enum class EditKey {
    None,
    Name,
    Pronouns,
    Persona,
}

/** 编辑类型显示名称扩展 */
@Composable
private fun EditKey.toDisplayName(): String {
    return when (this) {
        EditKey.None -> ""
        EditKey.Name -> stringResource(R.string.str_name)
        EditKey.Pronouns -> stringResource(R.string.str_pronouns)
        EditKey.Persona -> stringResource(R.string.str_persona)
    }
}

/** 个人设置页面主界面 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MySettingScreen(
    userProfile: UserProfile,
    onBack: () -> Unit = {},
    onSelectAvatar: () -> Unit = {},
    onClickName: () -> Unit = {},
    onClickPronouns: () -> Unit = {},
    onClickPersona: () -> Unit = {},
    onSave: () -> Unit = {},
    isSaving: Boolean = false,
) {
    Scaffold(
        modifier = Modifier.background(HeartColor.primaryColor),
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.str_edit_my_persona),
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 20.sp,
                    )
                },
                navigationIcon = {
                    Image(
                        modifier =
                            Modifier
                                .padding(horizontal = 12.dp)
                                .noRippleClickable { onBack() },
                        painter = painterResource(R.drawable.back),
                        contentDescription = null,
                    )
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )
        },
        containerColor = Color(0XFF1C1523),
    ) { innerPadding ->
        Column(modifier = Modifier.padding(innerPadding)) {
            Spacer(Modifier.height(16.dp))

            // 头像区域
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                AvatarSection(avatar = userProfile.avatar ?: "", onSelectAvatar = onSelectAvatar)
            }

            Spacer(Modifier.height(46.dp))

            val horizontalPadding = 16

            // 设置项区域
            SettingSection {
                MySettingItem(
                    key = stringResource(R.string.str_name),
                    value = userProfile.nickname,
                    horizontalPadding = horizontalPadding,
                    onClick = onClickName,
                )
                SettingDivider()
                MySettingItem(
                    key = stringResource(R.string.str_pronouns),
                    value = userProfile.pronouns(),
                    horizontalPadding = horizontalPadding,
                    onClick = onClickPronouns,
                )
                SettingDivider()
                MySettingItem(
                    key = stringResource(R.string.str_persona),
                    value = userProfile.description ?: "",
                    horizontalPadding = horizontalPadding,
                    onClick = onClickPersona,
                )
            }

            Spacer(Modifier.weight(1f))

            SaveButton(onSave = onSave, isSaving = isSaving)

            Spacer(Modifier.height(60.dp))
        }
    }
}

/** 头像选择区域 */
@Composable
private fun AvatarSection(avatar: String, onSelectAvatar: () -> Unit) {
    Box(
        modifier =
            Modifier
                .size(120.dp)
                .background(color = Color.White, shape = CircleShape)
                .padding(4.dp),
        contentAlignment = Alignment.Center,
    ) {
        AsyncImage(
            modifier = Modifier
                .fillMaxSize()
                .clip(CircleShape),
            model = ImageRequest.Builder(LocalContext.current)
                .data(avatar)
                .build(),
            placeholder = painterResource(R.drawable.app_icon),
            error = painterResource(R.drawable.app_icon),
            contentDescription = null,
        )
        Image(
            modifier =
                Modifier
                    .size(40.dp)
                    .align(Alignment.BottomEnd)
                    .noRippleClickable {
                        onSelectAvatar()
                    },
            painter = painterResource(R.drawable.icon_camera),
            contentDescription = null,
        )
    }
}

/** 设置项组件 */
@Composable
fun MySettingItem(
    key: String,
    value: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    horizontalPadding: Int,
) {
    Row(
        modifier =
            modifier
                .fillMaxWidth()
                .height(48.dp)
                .padding(horizontal = horizontalPadding.dp)
                .noRippleClickable { onClick() },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text = key, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
        Spacer(Modifier.width(8.dp))
        Text(
            text = value,
            fontSize = 14.sp,
            fontWeight = FontWeight.Normal,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            color = Color.White.copy(0.55f),
            textAlign = TextAlign.End,
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.width(8.dp))
        Image(painter = painterResource(R.drawable.icon_next), contentDescription = null)
    }
}

/** 保存按钮组件 */
@Composable
fun SaveButton(onSave: () -> Unit, isSaving: Boolean = false) {
    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
                .height(50.dp)
                .background(
                    brush =
                        Brush.linearGradient(
                            colors =
                                if (isSaving) {
                                    listOf(Color(0xFF666666), Color(0xFF888888))
                                } else {
                                    listOf(Color(0xFFC122FF), Color(0xFFFF905D))
                                }
                        ),
                    shape = RoundedCornerShape(25.dp),
                )
                .noRippleClickable {
                    if (!isSaving) {
                        onSave()
                    }
                }
    ) {
        if (isSaving) {
            // 显示加载动画
            CircularProgressIndicator(
                modifier = Modifier
                    .align(Alignment.Center)
                    .size(24.dp),
                color = Color.White,
                strokeWidth = 2.dp,
            )
        } else {
            Text(
                modifier = Modifier.align(Alignment.Center),
                text = stringResource(R.string.save),
                fontSize = 16.sp,
                fontWeight = FontWeight.Normal,
                color = Color.White,
            )
        }
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
    Box(
        modifier = Modifier
            .fillMaxSize()
            .imePadding()
            .noRippleClickable { onDismiss() }) {
        Column(
            modifier =
                Modifier
                    .align(Alignment.BottomCenter)
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
                    Modifier
                        .padding(16.dp)
                        .align(Alignment.End)
                        .noRippleClickable { onDismiss() },
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
            SaveButton(onSave = { onSave(editKey, editValue) })

            Spacer(Modifier.height(60.dp))
        }
    }
}

/** 编辑内容组件 */
@Composable
private fun EditContent(editKey: EditKey, editValue: String, onValueChange: (String) -> Unit) {
    when (editKey) {
        EditKey.Name -> {
            NameEditField(value = editValue, onValueChange = onValueChange)
        }

        EditKey.Persona -> {
            PersonaEditField(value = editValue, onValueChange = onValueChange)
        }

        EditKey.Pronouns -> {
            PronounsEditField(value = editValue, onValueChange = onValueChange)
        }

        EditKey.None -> {
            // 空内容
        }
    }
}

/** 姓名编辑字段 */
@Composable
private fun NameEditField(value: String, onValueChange: (String) -> Unit) {
    Row(
        modifier =
            Modifier
                .padding(horizontal = 16.dp, vertical = 0.dp)
                .fillMaxWidth()
                .heightIn(min = 48.dp)
                .background(Color.White.copy(0.1f), RoundedCornerShape(8.dp))
                .border(
                    width = 0.5.dp,
                    color = Color.White.copy(0.2f),
                    shape = RoundedCornerShape(8.dp),
                ),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IntySmallTextField(
            modifier = Modifier.weight(1f),
            value = value,
            selection = value.length,
            onValueChange = onValueChange,
            maxLength = 50,
        )
    }
}

/** 角色描述编辑字段 */
@Composable
private fun PersonaEditField(value: String, onValueChange: (String) -> Unit) {
    val focusRequester = remember { FocusRequester() }
    Box(
        modifier =
            Modifier
                .padding(horizontal = 16.dp, vertical = 0.dp)
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
            modifier = Modifier
                .fillMaxSize()
                .focusRequester(focusRequester),
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
            modifier = Modifier
                .align(Alignment.BottomEnd)
                .padding(12.dp, 8.dp),
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
            Modifier
                .padding(horizontal = 16.dp, vertical = 0.dp)
                .fillMaxWidth()
                .height(48.dp),
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
            Modifier
                .weight(1f)
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
private fun MySettingScreenPreview() {
    MySettingScreen(userProfile = UserProfile(nickname = "nick", id = "12345", avatar = ""))
}

@Preview(showBackground = true)
@Composable
fun SaveButtonPreview() {
    SaveButton(onSave = {}, isSaving = false)
}

@Preview(showBackground = true)
@Composable
fun SaveButtonLoadingPreview() {
    SaveButton(onSave = {}, isSaving = true)
}
