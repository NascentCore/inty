package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.PersonaPreferenceStore
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.ui.IntelliMateDivider
import ai.sxwl.android.design.ui.SettingsArrowItem
import ai.sxwl.android.design.ui.SettingsItemData
import ai.sxwl.android.design.ui.SettingsItemGroup
import ai.sxwl.android.design.ui.SettingsSwitchItem
import ai.sxwl.android.firebase.FirebaseManager
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
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
import kotlin.math.roundToInt
import kotlinx.coroutines.launch

private const val USER_MANUAL_NOTION_URL =
    "https://www.notion.so/IntelliMate-Help-Center-2b88c199b74b808a985bcaa64e36c322"

/** 聊天设置抽屉组件 */
@Composable
fun ChatSettingsDrawer(
    chatViewModel: ChatViewModel,
    agentInfo: AgentInfo?,
    drawerState: MutableState<DrawerValue>,
    onKeepTalkingChange: (Boolean) -> Unit,
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    // Keep talking全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val showKeepTalking by SettingStateManager.showKeepTalkingFlow.collectAsState()

    // Auto-play voice messages全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val autoPlayVoice by SettingStateManager.autoPlayAudioFlow.collectAsState()

    // Auto-play animated background全局设置
    val autoPlayAnimation by SettingStateManager.autoPlayAnimationFlow.collectAsState()

    // Show scene action button全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val showSceneActionButton by SettingStateManager.showSceneActionButtonFlow.collectAsState()
    val chatFontSize by SettingStateManager.chatFontSizeFlow.collectAsState()

    val horizontalPadding = 16
    val preferenceFlow = remember(context) { PersonaPreferenceStore.preferenceFlow(context) }
    val userPreference by preferenceFlow.collectAsState(initial = "")

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
    var showFontSizeDialog by rememberSaveable { mutableStateOf(false) }
    var pendingFontSize by rememberSaveable {
        mutableFloatStateOf(SettingStateManager.CHAT_FONT_SIZE_DEFAULT_SP)
    }

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
                Column(modifier = Modifier.padding(horizontal = horizontalPadding.dp)) {
                    SettingsItemGroup(modifier = Modifier) {
                        SettingsArrowItem(
                            item =
                                SettingsItemData.CommonItemData(
                                    title = stringResource(R.string.str_name),
                                    content = userProfileState.nickname.ifEmpty { "Guest" },
                                ),
                            isInGroup = true,
                            fontLight = true,
                            horizontalPadding = horizontalPadding,
                            contentMaxLines = 1,
                            onItemClick = {
                                // 检查是否已登录
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
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
                        IntelliMateDivider()
                        SettingsArrowItem(
                            item =
                                SettingsItemData.CommonItemData(
                                    title = stringResource(R.string.str_pronouns),
                                    content = userProfileState.pronouns(),
                                ),
                            isInGroup = true,
                            fontLight = true,
                            horizontalPadding = horizontalPadding,
                            contentMaxLines = 1,
                            onItemClick = {
                                // 检查是否已登录
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
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
                        IntelliMateDivider()
                        SettingsArrowItem(
                            item =
                                SettingsItemData.CommonItemData(
                                    title = stringResource(R.string.chat_settings_preference_title),
                                    content =
                                        userPreference.ifBlank {
                                            stringResource(
                                                R.string.chat_settings_preference_placeholder
                                            )
                                        },
                                    arrow = true,
                                ),
                            isInGroup = true,
                            fontLight = true,
                            horizontalPadding = horizontalPadding,
                            contentMaxLines = 1,
                            onItemClick = {
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "edit_preference",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                editKey = EditKey.Preference
                                editValue = userPreference
                            },
                        )
                        IntelliMateDivider()
                        SettingsArrowItem(
                            item =
                                SettingsItemData.CommonItemData(
                                    title = stringResource(R.string.str_persona),
                                    content = userProfileState.description ?: "Edit",
                                ),
                            isInGroup = true,
                            fontLight = true,
                            horizontalPadding = horizontalPadding,
                            contentMaxLines = 1,
                            onItemClick = {
                                // 检查是否已登录
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
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

                Column(modifier = Modifier.padding(horizontal = horizontalPadding.dp)) {
                    SettingsItemGroup {
                        // Show "Keep Talking" button开关
                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title =
                                        stringResource(R.string.chat_settings_show_keep_talking) +
                                            "青青河边草，有有利到寒假工i哦啊个",
                                    checked = showKeepTalking,
                                ),
                            fontLight = true,
                            isInGroup = true,
                            horizontalPadding = horizontalPadding,
                            openedIconRes = R.drawable.opened,
                            closedIconRes = R.drawable.closed,
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

                        IntelliMateDivider()

                        // Auto-play voice messages开关
                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title = stringResource(R.string.chat_settings_auto_play_voice),
                                    checked = autoPlayVoice,
                                ),
                            fontLight = true,
                            isInGroup = true,
                            horizontalPadding = horizontalPadding,
                            openedIconRes = R.drawable.opened,
                            closedIconRes = R.drawable.closed,
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

                        IntelliMateDivider()

                        // Auto-play animated background开关
                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title =
                                        stringResource(
                                            R.string.chat_settings_auto_play_animation
                                        ),
                                    checked = autoPlayAnimation,
                                ),
                            fontLight = true,
                            isInGroup = true,
                            horizontalPadding = horizontalPadding,
                            openedIconRes = R.drawable.opened,
                            closedIconRes = R.drawable.closed,
                            onCheckChanged = { enabled ->
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "toggle_auto_play_animation",
                                        "enabled" to enabled,
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                SettingStateManager.updateAutoPlayAnimation(enabled)
                            },
                        )

                        IntelliMateDivider()

                        // Show scene action button开关
                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title =
                                        stringResource(
                                            R.string.chat_settings_show_scene_action_button
                                        ),
                                    checked = showSceneActionButton,
                                ),
                            fontLight = true,
                            isInGroup = true,
                            horizontalPadding = horizontalPadding,
                            openedIconRes = R.drawable.opened,
                            closedIconRes = R.drawable.closed,
                            onCheckChanged = { enabled ->
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "toggle_show_scene_action_button",
                                        "enabled" to enabled,
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                SettingStateManager.updateShowSceneActionButton(enabled)
                            },
                        )

                        IntelliMateDivider()

                        // Font size row
                        SettingsArrowItem(
                            item =
                                SettingsItemData.CommonItemData(
                                    title = stringResource(R.string.chat_settings_font_size),
                                    content =
                                        stringResource(
                                            R.string.chat_settings_font_size_value,
                                            chatFontSize.roundToInt(),
                                        ),
                                    arrow = true,
                                ),
                            fontLight = true,
                            isInGroup = true,
                            horizontalPadding = horizontalPadding,
                            onItemClick = {
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "open_font_size_slider",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                pendingFontSize = chatFontSize
                                showFontSizeDialog = true
                            },
                        )
                    }
                }

                Spacer(Modifier.height(30.dp))

                Text(
                    text = stringResource(R.string.chat_settings_support_resources_title),
                    modifier = Modifier.padding(start = 16.dp),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )

                Spacer(Modifier.height(14.dp))

                Column(modifier = Modifier.padding(horizontal = horizontalPadding.dp)) {
                    SettingsItemGroup {
                        // 用户手册入口
                        SettingsArrowItem(
                            item =
                                SettingsItemData.CommonItemData(
                                    title =
                                        stringResource(R.string.chat_settings_user_manual_title),
                                    content = "",
                                    arrow = true,
                                ),
                            fontLight = true,
                            isInGroup = true,
                            horizontalPadding = horizontalPadding,
                            onItemClick = {
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "user_manual",
                                        "destination" to "notion",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                val manualIntent =
                                    Intent(Intent.ACTION_VIEW, Uri.parse(USER_MANUAL_NOTION_URL))
                                context.startActivity(manualIntent)
                            },
                        )

                        IntelliMateDivider()

                        // Feedback入口
                        SettingsArrowItem(
                            item =
                                SettingsItemData.CommonItemData(
                                    title = stringResource(R.string.feedback_title),
                                    content = "",
                                    arrow = true,
                                ),
                            fontLight = true,
                            isInGroup = true,
                            horizontalPadding = horizontalPadding,
                            onItemClick = {
                                // 检查是否已登录
                                if (
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                ) {
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                        FirebaseManager.safeEventParams(
                                            "click_type" to "feedback",
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    ReportActivity.launchFeedback(context)
                                }
                            },
                        )

                        agentInfo?.let { agent ->
                            IntelliMateDivider()

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
                                horizontalPadding = horizontalPadding,
                                onItemClick = {
                                    // 检查是否已登录
                                    if (
                                        IntySetting.isLogin() &&
                                            IntySetting.getCurToken().isNotEmpty()
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
                        when (key) {
                            EditKey.Preference -> {
                                editKey = EditKey.None
                                coroutineScope.launch {
                                    PersonaPreferenceStore.savePreference(
                                        context,
                                        value.trim(),
                                    )
                                }
                            }
                            else -> {
                                modifyProfileViewModel.changeUserProfile(key, value)
                                editKey = EditKey.None
                                // 直接保存，事件监听会自动刷新UI
                                modifyProfileViewModel.onSave()
                            }
                        }
                    },
                    onValueChange = { value -> editValue = value },
                )
            }
        }

        if (showFontSizeDialog) {
            Dialog(
                onDismissRequest = { showFontSizeDialog = false },
                properties = DialogProperties(usePlatformDefaultWidth = false),
            ) {
                Column(
                    modifier =
                        Modifier.padding(horizontal = 24.dp)
                            .clip(RoundedCornerShape(24.dp))
                            .background(Color(0xFF241533))
                            .widthIn(min = 280.dp, max = 360.dp)
                            .padding(horizontal = 20.dp, vertical = 24.dp)
                ) {
                    Text(
                        text = stringResource(R.string.chat_settings_font_size_dialog_title),
                        fontSize = 20.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White,
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = stringResource(R.string.chat_settings_font_size_dialog_description),
                        fontSize = 14.sp,
                        color = Color.White.copy(alpha = 0.75f),
                    )
                    Spacer(modifier = Modifier.height(20.dp))
                    Text(
                        text =
                            stringResource(
                                R.string.chat_settings_font_size_value,
                                pendingFontSize.roundToInt(),
                            ),
                        fontSize = 14.sp,
                        color = Color.White.copy(alpha = 0.8f),
                    )
                    Slider(
                        value = pendingFontSize,
                        onValueChange = { pendingFontSize = it },
                        valueRange =
                            SettingStateManager.CHAT_FONT_SIZE_MIN_SP..SettingStateManager
                                    .CHAT_FONT_SIZE_MAX_SP,
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = stringResource(R.string.chat_settings_font_size_preview_label),
                        fontSize = 12.sp,
                        color = Color.White.copy(alpha = 0.6f),
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = stringResource(R.string.chat_settings_font_size_preview_sample),
                        fontSize = pendingFontSize.sp,
                        color = Color.White,
                    )
                    Spacer(modifier = Modifier.height(24.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End,
                    ) {
                        TextButton(
                            onClick = {
                                pendingFontSize = SettingStateManager.CHAT_FONT_SIZE_DEFAULT_SP
                            }
                        ) {
                            Text(text = stringResource(R.string.str_reset))
                        }
                        Spacer(modifier = Modifier.width(4.dp))
                        TextButton(onClick = { showFontSizeDialog = false }) {
                            Text(text = stringResource(R.string.cancel))
                        }
                        Spacer(modifier = Modifier.width(8.dp))
                        Button(
                            onClick = {
                                val newSize =
                                    pendingFontSize
                                        .roundToInt()
                                        .coerceIn(
                                            SettingStateManager.CHAT_FONT_SIZE_MIN_SP.toInt(),
                                            SettingStateManager.CHAT_FONT_SIZE_MAX_SP.toInt(),
                                        )
                                        .toFloat()
                                SettingStateManager.updateChatFontSize(newSize)
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "update_font_size",
                                        "font_size_sp" to newSize,
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                showFontSizeDialog = false
                            }
                        ) {
                            Text(text = stringResource(R.string.save))
                        }
                    }
                }
            }
        }
    }
}
