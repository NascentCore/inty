package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.ui.SettingsArrowItem
import ai.sxwl.android.design.ui.SettingsItemData
import ai.sxwl.android.design.ui.SettingsSwitchItem
import ai.sxwl.android.firebase.FirebaseManager
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
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
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.compose.LifecycleResumeEffect
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.intellimate.R
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.profile.ModifyProfileViewModel
import com.ai.intellimate.ui.MyModalNavigationDrawer
import com.ai.intellimate.ui.components.EditDialog
import com.ai.intellimate.ui.components.EditKey
import com.ai.intellimate.ui.components.ProfileInfoItem

/** 聊天设置抽屉组件 */
@Composable
fun ChatSettingsDrawer(
    chatViewModel: ChatViewModel,
    agentInfo: AgentInfo?,
    drawerState: MutableState<DrawerValue>,
    onKeepTalkingChange: (Boolean) -> Unit,
) {
    val context = LocalContext.current
    // Keep talking全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val showKeepTalking by SettingStateManager.showKeepTalkingFlow.collectAsState()

    // Auto-play voice messages全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val autoPlayVoice by SettingStateManager.autoPlayAudioFlow.collectAsState()

    val horizontalPadding = 16

    // 在组件初始化时立即更新用户信息,未添加这部分触发更新userInfo的时候，会因为在chatViewModel中虽然更新了userProfile
    // 但是userProfileState并没有正确触发数据流的更新，引起UI层数据不能正确显示真实数据的问题。
    LaunchedEffect(chatViewModel) { chatViewModel.updateUserInfo() }

    val userProfileState by chatViewModel.userProfile.collectAsState()

    LifecycleResumeEffect(chatViewModel) {
        chatViewModel.updateUserInfo()
        onPauseOrDispose {}
    }

    // 本地编辑状态（与 MySettingActivity 一致）
    var editKey by rememberSaveable { mutableStateOf(EditKey.None) }
    var editValue by rememberSaveable { mutableStateOf("") }

    // 复用 MySettingViewModel 的保存逻辑
    val modifyProfileViewModel: ModifyProfileViewModel = viewModel()

    LaunchedEffect(userProfileState) { modifyProfileViewModel.init(userProfileState) }

    // 监听用户信息更新事件，及时刷新UI
    LaunchedEffect(modifyProfileViewModel) {
        modifyProfileViewModel.events.collect { event ->
            when (event) {
                com.ai.intellimate.ViewModelEvent.UserProfileUpdated -> {
                    // 用户信息更新后，立即刷新ChatViewModel中的用户信息
                    chatViewModel.updateUserInfo()
                }

                else -> {}
            }
        }
    }

    // 移除TheRouter拦截器，使用其他方式处理用户信息更新

    MyModalNavigationDrawer(
        modifier = Modifier,
        drawerState = drawerState,
        drawerContent = {
            Column(
                modifier =
                    Modifier.width(319.dp)
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
                        Modifier.padding(horizontal = horizontalPadding.dp)
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
                    ProfileInfoItem(
                        key = stringResource(R.string.str_name),
                        value = userProfileState.nickname.ifEmpty { "Guest" },
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否已登录
                            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "edit_name",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                editKey = EditKey.Name
                                editValue = userProfileState.nickname
                            }
                        },
                    )
                    ProfileInfoItem(
                        key = stringResource(R.string.str_pronouns),
                        value = userProfileState.pronouns(),
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否已登录
                            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "edit_pronouns",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                editKey = EditKey.Pronouns
                                editValue = userProfileState.gender ?: ""
                            }
                        },
                    )
                    ProfileInfoItem(
                        key = stringResource(R.string.str_persona),
                        value = userProfileState.description ?: "Edit",
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否已登录
                            if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "edit_persona",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                editKey = EditKey.Persona
                                editValue = userProfileState.description ?: ""
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

                // 参照My Persona的样式，使用Column包裹，外层padding，内层item也有padding
                Column(
                    modifier =
                        Modifier.padding(horizontal = horizontalPadding.dp)
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
                    // Show "Keep Talking" button开关
                    SettingsSwitchItem(
                        item =
                            SettingsItemData.SwitchItemData(
                                title = stringResource(R.string.chat_settings_show_keep_talking),
                                checked = showKeepTalking,
                            ),
                        fontLight = true,
                        isInGroup = true,
                        horizontalPadding = horizontalPadding, // 使用与My Persona相同的padding
                        openedIconRes = R.drawable.opened, // 传入app模块的资源
                        closedIconRes = R.drawable.closed, // 传入app模块的资源
                        onCheckChanged = { enabled ->
                            FirebaseManager.logEvent(
                                FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                FirebaseManager.safeEventParams(
                                    "click_type" to "toggle_keep_talking",
                                    "enabled" to enabled,
                                    "timestamp" to System.currentTimeMillis(),
                                ),
                            )
                            SettingStateManager.updateShowKeepTalking(enabled)
                            onKeepTalkingChange(enabled)
                        },
                    )

                    // Auto-play voice messages开关
                    SettingsSwitchItem(
                        item =
                            SettingsItemData.SwitchItemData(
                                title = stringResource(R.string.chat_settings_auto_play_voice),
                                checked = autoPlayVoice,
                            ),
                        fontLight = true,
                        isInGroup = true,
                        horizontalPadding = horizontalPadding, // 使用与My Persona相同的padding
                        openedIconRes = R.drawable.opened, // 传入app模块的资源
                        closedIconRes = R.drawable.closed, // 传入app模块的资源
                        onCheckChanged = { enabled ->
                            FirebaseManager.logEvent(
                                FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                FirebaseManager.safeEventParams(
                                    "click_type" to "toggle_auto_play_voice",
                                    "enabled" to enabled,
                                    "timestamp" to System.currentTimeMillis(),
                                ),
                            )
                            SettingStateManager.updateAutoPlayAudio(enabled)
                        },
                    )

                    agentInfo?.let { agent ->
                        // 举报入口
                        SettingsArrowItem(
                            item =
                                SettingsItemData.CommonItemData(
                                    title = stringResource(R.string.str_report),
                                    content = "",
                                    arrow = true,
                                ),
                            fontLight = true,
                            isInGroup = true,
                            horizontalPadding = horizontalPadding, // 使用与My Persona相同的padding
                            onItemClick = {
                                // 检查是否已登录
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                        FirebaseManager.safeEventParams(
                                            "click_type" to "report",
                                            "agent_id" to agent.id,
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    ReportActivity.launch(context, agent.id, "AGENT")
                                }
                            },
                        )
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
                        modifyProfileViewModel.changeUserProfile(key, value)
                        editKey = EditKey.None
                        // 直接保存，事件监听会自动刷新UI
                        modifyProfileViewModel.onSave()
                    },
                    onValueChange = { value -> editValue = value },
                )
            }
        }
    }
}
