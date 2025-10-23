package com.ai.inty.chat.ui

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.MutableState
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.inty.LoginActivity
import com.ai.inty.R
import com.ai.inty.ReportActivity
import com.ai.inty.base.MyModalNavigationDrawer
import com.ai.inty.billing.BillingRepository
import com.ai.inty.chat.ChatViewModel
import com.ai.inty.ui.components.EditDialog
import com.ai.inty.ui.components.EditKey
import com.ai.inty.ui.components.MySettingItem
import com.ai.inty.viewmodels.MySettingViewModel

/** 聊天设置抽屉组件 */
@Composable
fun ChatSettingsDrawer(
    chatViewModel: ChatViewModel,
    agentInfo: AgentInfo?,
    drawerState: MutableState<DrawerValue>,
    onKeepTalkingChange: (Boolean) -> Unit,
) {
    val context = LocalContext.current
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    // Keep talking二状态设置：默认跟随全局设置
    var agentKeepTalking by
    remember(agentInfo?.id) {
        mutableStateOf(
            agentInfo?.let {
                // 获取角色专用设置，如果不存在则使用全局设置
                IntySetting.getAgentKeepTalking(it.id) ?: IntySetting.isShowKeepTalking()
            } ?: false
        )
    }

    val horizontalPadding = 16

    // 在组件初始化时立即更新用户信息,未添加这部分触发更新userInfo的时候，会因为在chatViewModel中虽然更新了userProfile
    //但是userProfileState并没有正确触发数据流的更新，引起UI层数据不能正确显示真实数据的问题。
    LaunchedEffect(chatViewModel) {
        chatViewModel.updateUserInfo()
    }

    val userProfileState by chatViewModel.userProfile.collectAsState()

    LifecycleResumeEffect(chatViewModel) {
        chatViewModel.updateUserInfo()
        onPauseOrDispose {}
    }

    // 本地编辑状态（与 MySettingActivity 一致）
    var editKey by rememberSaveable { mutableStateOf(EditKey.None) }
    var editValue by rememberSaveable { mutableStateOf("") }

    // 复用 MySettingViewModel 的保存逻辑
    val mySettingViewModel: MySettingViewModel = viewModel()

    LaunchedEffect(userProfileState) { mySettingViewModel.init(userProfileState) }

    // 移除TheRouter拦截器，使用其他方式处理用户信息更新

    MyModalNavigationDrawer(
        modifier = Modifier,
        drawerState = drawerState,
        drawerContent = {
            Column(
                modifier =
                    Modifier
                        .width(319.dp)
                        .fillMaxHeight()
                        .background(
                            brush =
                                Brush.verticalGradient(
                                    colors = listOf(Color(0xFF322341), Color(0xFF120E24))
                                )
                        )
            ) {
                Text(
                    text = stringResource(R.string.chat_settings_my_persona_title),
                    modifier = Modifier.padding(top = 58.dp, start = 16.dp),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )

                Spacer(Modifier.height(14.dp))

                Column(
                    modifier =
                        Modifier
                            .padding(horizontal = horizontalPadding.dp)
                            .fillMaxWidth()
                            .border(
                                brush =
                                    Brush.linearGradient(
                                        colors =
                                            listOf(
                                                Color.Transparent,
                                                Color.White.copy(0.2f),
                                                Color.Transparent,
                                            )
                                    ),
                                width = 1.dp,
                                shape = RoundedCornerShape(8.dp),
                            )
                            .background(color = Color(0x3378599A), shape = RoundedCornerShape(8.dp))
                ) {
                    MySettingItem(
                        key = stringResource(R.string.str_name),
                        value = userProfileState.nickname.ifEmpty { "Guest" },
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否正式登录（非游客且已登录）
                            if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                editKey = EditKey.Name
                                editValue = userProfileState.nickname
                            } else {
                                // 未登录或游客时跳转到登录页面
                                LoginActivity.launch(context)
                            }
                        },
                    )
                    MySettingItem(
                        key = stringResource(R.string.str_pronouns),
                        value = userProfileState.pronouns(),
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否正式登录（非游客且已登录）
                            if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                editKey = EditKey.Pronouns
                                editValue = userProfileState.gender ?: ""
                            } else {
                                // 未登录或游客时跳转到登录页面
                                LoginActivity.launch(context)
                            }
                        },
                    )
                    MySettingItem(
                        key = stringResource(R.string.str_persona),
                        value = userProfileState.description ?: "Edit",
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否正式登录（非游客且已登录）
                            if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                editKey = EditKey.Persona
                                editValue = userProfileState.description ?: ""
                            } else {
                                // 未登录或游客时跳转到登录页面
                                LoginActivity.launch(context)
                            }
                        },
                    )
                }

                Spacer(Modifier.height(30.dp))

                Text(
                    text = stringResource(R.string.chat_settings_settings_title),
                    modifier = Modifier.padding(start = 16.dp),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )

                Spacer(Modifier.height(14.dp))

                Column(
                    modifier =
                        Modifier
                            .padding(horizontal = horizontalPadding.dp)
                            .fillMaxWidth()
                            .border(
                                brush =
                                    Brush.linearGradient(
                                        colors =
                                            listOf(
                                                Color.Transparent,
                                                Color.White.copy(0.2f),
                                                Color.Transparent,
                                            )
                                    ),
                                width = 1.dp,
                                shape = RoundedCornerShape(8.dp),
                            )
                            .background(color = Color(0x3378599A), shape = RoundedCornerShape(8.dp))
                ) {
                    agentInfo?.let { agent ->

                        // 举报入口
                        Row(
                            modifier =
                                Modifier
                                    .fillMaxWidth()
                                    .height(56.dp)
                                    .padding(horizontal = horizontalPadding.dp)
                                    .noRippleClickable {
                                        // 检查是否正式登录（非游客且已登录）
                                        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                            ReportActivity.launch(context, agent.id, "AGENT")
                                        } else {
                                            // 未登录或游客时跳转到登录页面
                                            LoginActivity.launch(context)
                                        }
                                    },
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Text(
                                text = stringResource(R.string.str_report),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Normal,
                                color = Color.White,
                            )
                            Spacer(Modifier.weight(1f))
                            Image(
                                painter = painterResource(R.drawable.icon_next),
                                contentDescription = null,
                            )
                        }
                    }
                }
            }
        },
    ) {
        // 应该放主屏内容的位置
        // 编辑弹窗（与 MySettingActivity 同样的 UI 交互）
        if (editKey != EditKey.None) {
            Dialog(
                onDismissRequest = { editKey = EditKey.None },
                properties = DialogProperties(usePlatformDefaultWidth = false),
            ) {
                EditDialog(
                    editKey = editKey,
                    editValue = editValue,
                    onDismiss = { editKey = EditKey.None },
                    onSave = { key, value ->
                        mySettingViewModel.changeUserProfile(key, value)
                        editKey = EditKey.None
                        // 直接保存并刷新本地展示
                        mySettingViewModel.onSave()
                        chatViewModel.updateUserInfo()
                    },
                    onValueChange = { value -> editValue = value },
                )
            }
        }
    }
}
