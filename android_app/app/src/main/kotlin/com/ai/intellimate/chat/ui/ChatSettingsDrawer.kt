package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.TextToSpeechVoiceOption
import ai.sxwl.android.data.billing.BillingRepository
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.data.store.SettingStateManager
import ai.sxwl.android.design.theme.textOnLightSurface
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
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.consumeWindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.navigation.NavController
import com.ai.intellimate.R
import com.ai.intellimate.ui.ChatDialogData
import com.ai.intellimate.ui.MyModalNavigationDrawer
import com.ai.intellimate.ui.UnlimitChatDialog
import com.ai.intellimate.xb.navigation.Routes
import kotlin.math.roundToInt
import kotlinx.coroutines.launch

private const val USER_MANUAL_NOTION_URL =
    "https://www.notion.so/IntelliMate-Help-Center-2b88c199b74b808a985bcaa64e36c322"

private const val CHAT_MODEL_ID_DEFAULT = "default"
private const val CHAT_MODEL_ID_GPT_5_2 = "gpt5_2"
private const val CHAT_MODEL_ID_CLAUDE_OPUS_4_5 = "claude_opus_4_5"
private const val CHAT_MODEL_ID_GEMINI_3_FLASH = "gemini_3_flash"
private const val VOICE_MENU_VISIBLE_ENTRY_COUNT = 9

private data class ChatModelOption(val id: String, val labelResId: Int)

private val CHAT_MODEL_OPTIONS =
    listOf(
        ChatModelOption(CHAT_MODEL_ID_DEFAULT, R.string.chat_settings_model_default),
        ChatModelOption(CHAT_MODEL_ID_GPT_5_2, R.string.chat_settings_model_gpt_5_2),
        ChatModelOption(
            CHAT_MODEL_ID_CLAUDE_OPUS_4_5,
            R.string.chat_settings_model_claude_opus_4_5,
        ),
        ChatModelOption(CHAT_MODEL_ID_GEMINI_3_FLASH, R.string.chat_settings_model_gemini_3_flash),
    )

private fun chatModelLabelResId(modelId: String): Int {
    return when (modelId) {
        CHAT_MODEL_ID_DEFAULT -> R.string.chat_settings_model_default
        CHAT_MODEL_ID_GPT_5_2 -> R.string.chat_settings_model_gpt_5_2
        CHAT_MODEL_ID_CLAUDE_OPUS_4_5 -> R.string.chat_settings_model_claude_opus_4_5
        CHAT_MODEL_ID_GEMINI_3_FLASH -> R.string.chat_settings_model_gemini_3_flash
        else -> R.string.chat_settings_model_default
    }
}

/** 聊天设置抽屉组件 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatSettingsDrawer(
    agentInfo: AgentInfo?,
    drawerState: MutableState<DrawerValue>,
    onKeepTalkingChange: (Boolean) -> Unit,
    navController: NavController,
    selectedChatVoiceId: String?,
    chatVoiceOptions: List<TextToSpeechVoiceOption>,
    isLoadingChatVoices: Boolean,
    onChatVoiceSelected: (String?) -> Unit,
    showBackButton: Boolean = false, // 是否在独立 ChatScreen 场景下（没有底部导航栏）
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    // 订阅状态检查
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
    // Keep talking全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val showKeepTalking by SettingStateManager.showKeepTalkingFlow.collectAsState(false)

    // Auto-play voice messages全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val autoPlayVoice by SettingStateManager.autoPlayAudioFlow.collectAsState(false)

    // Auto-play animated background全局设置
    val autoPlayAnimation by SettingStateManager.autoPlayAnimationFlow.collectAsState()
    val textStreaming by SettingStateManager.textStreaming.collectAsState()

    // Show scene action button全局设置 - 使用SettingStateManager的Flow来监听设置变化
    val showSceneActionButton by SettingStateManager.showSceneActionButtonFlow.collectAsState()
    val chatFontSize by SettingStateManager.chatFontSizeFlow.collectAsState()
    val chatModelId by SettingStateManager.chatModelIdFlow.collectAsState()

    // 消息列表是否全屏全局设置
    val chatListFullScreen by SettingStateManager.chatListFullScreenFlow.collectAsState()

    val horizontalPadding = 16
    val dropdownItemHeight = dimensionResource(id = R.dimen.chat_settings_dropdown_item_height)
    val voiceMenuMaxHeight = dropdownItemHeight * VOICE_MENU_VISIBLE_ENTRY_COUNT
    var showFontSizeDialog by rememberSaveable { mutableStateOf(false) }
    var showVipDialogPageSource by rememberSaveable { mutableStateOf<String?>(null) }
    var showModelMenu by rememberSaveable { mutableStateOf(false) }
    var showVoiceMenu by rememberSaveable { mutableStateOf(false) }
    var pendingFontSize by rememberSaveable {
        mutableFloatStateOf(SettingStateManager.CHAT_FONT_SIZE_DEFAULT_SP)
    }

    MyModalNavigationDrawer(
        modifier = Modifier.consumeWindowInsets(WindowInsets.navigationBars),
        drawerState = drawerState,
        drawerContent = {
            Column(
                modifier =
                    Modifier.width(319.dp)
                        .fillMaxHeight()
                        .verticalScroll(rememberScrollState())
                        .background(
                            brush =
                                Brush.verticalGradient(
                                    colors = listOf(Color(0xFF322341), Color(0xFF120E24))
                                )
                        )
            ) {
                Text(
                    text = stringResource(R.string.chat_settings_settings_title),
                    modifier = Modifier.padding(top = 58.dp, start = 16.dp),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )

                Spacer(Modifier.height(10.dp))

                Column(modifier = Modifier.padding(horizontal = horizontalPadding.dp)) {
                    SettingsItemGroup {
                        // Show "Keep Talking" button开关：打开时需会员，关闭不判断
                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title =
                                        stringResource(R.string.chat_settings_show_keep_talking),
                                    checked = showKeepTalking,
                                ),
                            showVip = true,
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
                                if (enabled && !vipStatus.isSubscribed) {
                                    showVipDialogPageSource = "chat_settings_keep_talking"
                                    return@SettingsSwitchItem
                                }
                                coroutineScope.launch {
                                    SettingStateManager.updateShowKeepTalking(enabled)
                                }
                                onKeepTalkingChange(enabled)
                            },
                        )

                        IntelliMateDivider()

                        // Auto-play voice messages开关：打开时需会员，关闭不判断
                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title = stringResource(R.string.chat_settings_auto_play_voice),
                                    checked = autoPlayVoice,
                                ),
                            showVip = true,
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
                                if (enabled && !vipStatus.isSubscribed) {
                                    showVipDialogPageSource = "chat_settings_auto_play"
                                    return@SettingsSwitchItem
                                }
                                coroutineScope.launch {
                                    SettingStateManager.updateAutoPlayAudio(enabled)
                                }
                            },
                        )

                        IntelliMateDivider()

                        // Voice 音色（每个聊天独立设置）
                        androidx.compose.foundation.layout.Box {
                            val voiceOptionsForCurrentAgent =
                                remember(agentInfo?.gender, chatVoiceOptions) {
                                    filterChatVoiceOptionsByAgentGender(
                                        voices = chatVoiceOptions,
                                        agentGender = agentInfo?.gender,
                                    )
                                }
                            val selectedVoiceLabel =
                                when {
                                    isLoadingChatVoices ->
                                        stringResource(R.string.chat_settings_voice_loading)
                                    selectedChatVoiceId.isNullOrBlank() ->
                                        stringResource(R.string.chat_settings_voice_default)
                                    else ->
                                        voiceOptionsForCurrentAgent
                                            .firstOrNull { it.voiceId == selectedChatVoiceId }
                                            ?.name
                                            ?: stringResource(R.string.chat_settings_voice_default)
                                }

                            SettingsArrowItem(
                                item =
                                    SettingsItemData.CommonItemData(
                                        title = stringResource(R.string.chat_settings_voice_title),
                                        content = selectedVoiceLabel,
                                        arrow = true,
                                    ),
                                showVip = true,
                                fontLight = true,
                                isInGroup = true,
                                horizontalPadding = horizontalPadding,
                                onItemClick = {
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                        FirebaseManager.safeEventParams(
                                            "click_type" to "open_voice_menu",
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    if (!vipStatus.isSubscribed) {
                                        showVipDialogPageSource = "chat_settings_voice"
                                        FirebaseManager.logEvent(
                                            FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                            FirebaseManager.safeEventParams(
                                                "click_type" to
                                                    "open_voice_menu_requires_subscription",
                                                "timestamp" to System.currentTimeMillis(),
                                            ),
                                        )
                                        return@SettingsArrowItem
                                    }
                                    if (!isLoadingChatVoices) {
                                        showVoiceMenu = true
                                    }
                                },
                            )

                            DropdownMenu(
                                expanded = showVoiceMenu,
                                onDismissRequest = { showVoiceMenu = false },
                                modifier =
                                    Modifier.heightIn(max = voiceMenuMaxHeight)
                                        .background(
                                            MaterialTheme.colorScheme.surfaceContainerLowest
                                        ),
                            ) {
                                DropdownMenuItem(
                                    text = {
                                        Text(
                                            text =
                                                stringResource(
                                                    R.string.chat_settings_voice_default
                                                ),
                                            color = MaterialTheme.colorScheme.textOnLightSurface,
                                            style = MaterialTheme.typography.bodyMedium,
                                        )
                                    },
                                    onClick = {
                                        showVoiceMenu = false
                                        onChatVoiceSelected(null)
                                        FirebaseManager.logEvent(
                                            FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                            FirebaseManager.safeEventParams(
                                                "click_type" to "select_voice",
                                                "voice_id" to "default",
                                                "timestamp" to System.currentTimeMillis(),
                                            ),
                                        )
                                    },
                                )

                                voiceOptionsForCurrentAgent.forEach { option ->
                                    DropdownMenuItem(
                                        text = {
                                            Text(
                                                text = option.name,
                                                color =
                                                    MaterialTheme.colorScheme.textOnLightSurface,
                                                style = MaterialTheme.typography.bodyMedium,
                                            )
                                        },
                                        onClick = {
                                            showVoiceMenu = false
                                            onChatVoiceSelected(option.voiceId)
                                            FirebaseManager.logEvent(
                                                FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                                FirebaseManager.safeEventParams(
                                                    "click_type" to "select_voice",
                                                    "voice_id" to option.voiceId,
                                                    "timestamp" to System.currentTimeMillis(),
                                                ),
                                            )
                                        },
                                    )
                                }
                            }
                        }

                        IntelliMateDivider()

                        // 消息列表是否全屏开关
                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title =
                                        stringResource(
                                            R.string.chat_settings_chat_list_full_screen
                                        ),
                                    checked = chatListFullScreen,
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
                                        "click_type" to "toggle_chat_list_full_screen",
                                        "enabled" to enabled,
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                SettingStateManager.updateChatListFullScreen(enabled)
                            },
                        )

                        IntelliMateDivider()

                        // Auto-play animated background开关
                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title =
                                        stringResource(R.string.chat_settings_auto_play_animation),
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

                        SettingsSwitchItem(
                            item =
                                SettingsItemData.SwitchItemData(
                                    title = stringResource(R.string.chat_setting_text_streaming),
                                    checked = textStreaming,
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
                                        "click_type" to "toggle_text_streaming",
                                        "enabled" to enabled,
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                SettingStateManager.updateTextStreaming(enabled)
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
                                coroutineScope.launch {
                                    SettingStateManager.updateShowSceneActionButton(enabled)
                                }
                            },
                        )

                        IntelliMateDivider()

                        // Models 下拉菜单：仅 VIP 可切换模型，非 VIP 固定视为 Default 且点击弹出升级弹窗
                        androidx.compose.foundation.layout.Box {
                            val effectiveModelLabel =
                                if (vipStatus.isSubscribed) {
                                    stringResource(chatModelLabelResId(chatModelId))
                                } else {
                                    stringResource(R.string.chat_settings_model_default)
                                }
                            SettingsArrowItem(
                                item =
                                    SettingsItemData.CommonItemData(
                                        title = stringResource(R.string.chat_settings_models_title),
                                        content = effectiveModelLabel,
                                        arrow = true,
                                    ),
                                showVip = true,
                                fontLight = true,
                                isInGroup = true,
                                horizontalPadding = horizontalPadding,
                                onItemClick = {
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                        FirebaseManager.safeEventParams(
                                            "click_type" to "open_models_menu",
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    if (!vipStatus.isSubscribed) {
                                        showVipDialogPageSource = "chat_settings_model"
                                        return@SettingsArrowItem
                                    }
                                    showModelMenu = true
                                },
                            )

                            // 显式设置浅色背景，保证弹层与 textOnLightSurface 文字对比度一致
                            DropdownMenu(
                                expanded = showModelMenu,
                                onDismissRequest = { showModelMenu = false },
                                modifier =
                                    Modifier.background(
                                        MaterialTheme.colorScheme.surfaceContainerLowest
                                    ),
                            ) {
                                CHAT_MODEL_OPTIONS.forEach { option ->
                                    DropdownMenuItem(
                                        text = {
                                            Text(
                                                text = stringResource(option.labelResId),
                                                color =
                                                    MaterialTheme.colorScheme.textOnLightSurface,
                                                style = MaterialTheme.typography.bodyMedium,
                                            )
                                        },
                                        onClick = {
                                            showModelMenu = false

                                            // 检查订阅状态：如果未订阅且选择的不是Default，则跳转到订阅页面
                                            if (
                                                !vipStatus.isSubscribed &&
                                                    option.id != CHAT_MODEL_ID_DEFAULT
                                            ) {
                                                navController.navigate(
                                                    Routes.Me.vipCenter("chat_settings_model")
                                                )
                                                FirebaseManager.logEvent(
                                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                                    FirebaseManager.safeEventParams(
                                                        "click_type" to
                                                            "select_model_requires_subscription",
                                                        "model_id" to option.id,
                                                        "timestamp" to System.currentTimeMillis(),
                                                    ),
                                                )
                                            } else {
                                                // 已订阅或选择Default，允许选择
                                                val modelIdToSet =
                                                    if (option.id == CHAT_MODEL_ID_DEFAULT) {
                                                        CHAT_MODEL_ID_DEFAULT
                                                    } else {
                                                        option.id
                                                    }
                                                SettingStateManager.updateChatModelId(modelIdToSet)
                                                FirebaseManager.logEvent(
                                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                                    FirebaseManager.safeEventParams(
                                                        "click_type" to "select_model",
                                                        "model_id" to option.id,
                                                        "timestamp" to System.currentTimeMillis(),
                                                    ),
                                                )
                                            }
                                        },
                                    )
                                }
                            }
                        }

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

                Spacer(Modifier.height(20.dp))

                Text(
                    text = stringResource(R.string.chat_settings_support_resources_title),
                    modifier = Modifier.padding(start = 16.dp),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )

                Spacer(Modifier.height(10.dp))

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
                                val isLoggedIn =
                                    IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "feedback",
                                        "logged_in" to isLoggedIn,
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                if (isLoggedIn) {
                                    navController.navigate(
                                        Routes.Me.reportPage(
                                            isFeedback = true,
                                            targetType = "AGENT",
                                            targetId = agentInfo?.id ?: "",
                                        )
                                    )
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
                                    val isLoggedIn =
                                        IntySetting.isLogin() &&
                                            IntySetting.getCurToken().isNotEmpty()
                                    FirebaseManager.logEvent(
                                        FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                        FirebaseManager.safeEventParams(
                                            "click_type" to "report",
                                            "agent_id" to agent.id,
                                            "logged_in" to isLoggedIn,
                                            "timestamp" to System.currentTimeMillis(),
                                        ),
                                    )
                                    if (isLoggedIn) {
                                        navController.navigate(
                                            Routes.Me.reportPage(false, "AGENT", agent.id)
                                        )
                                    }
                                },
                            )
                        }
                    }
                }

                Spacer(Modifier.height(20.dp))
            }
        },
    ) {
        showVipDialogPageSource?.let { pageSource ->
            val data =
                ChatDialogData(
                    R.drawable.img_unlimit_dialog_bg,
                    stringResource(R.string.str_unlimit_dialog_content),
                    stringResource(R.string.str_unlimit_btn_text),
                )
            UnlimitChatDialog(
                data,
                onCancel = { showVipDialogPageSource = null },
                onSure = {
                    if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                        navController.navigate(Routes.Me.vipCenter(pageSource))
                    }
                    showVipDialogPageSource = null
                },
                onMoreInfo = {
                    if (IntySetting.isLogin() && IntySetting.getCurToken().isNotEmpty()) {
                        navController.navigate(Routes.Me.vipCenter(pageSource))
                    }
                    showVipDialogPageSource = null
                },
            )
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
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "font_size_reset",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                pendingFontSize = SettingStateManager.CHAT_FONT_SIZE_DEFAULT_SP
                            }
                        ) {
                            Text(text = stringResource(R.string.str_reset))
                        }
                        Spacer(modifier = Modifier.width(4.dp))
                        TextButton(
                            onClick = {
                                FirebaseManager.logEvent(
                                    FirebaseManager.Events.CHAT_SIDEBAR_CLICK,
                                    FirebaseManager.safeEventParams(
                                        "click_type" to "font_size_cancel",
                                        "timestamp" to System.currentTimeMillis(),
                                    ),
                                )
                                showFontSizeDialog = false
                            }
                        ) {
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
