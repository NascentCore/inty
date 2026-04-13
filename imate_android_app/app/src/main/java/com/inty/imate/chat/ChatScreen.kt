package com.inty.imate.chat

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.clickable
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Send
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation3.runtime.NavKey
import androidx.paging.LoadState
import androidx.paging.compose.collectAsLazyPagingItems
import androidx.paging.compose.itemKey
import coil3.compose.AsyncImage
import com.ai.core.ui.theme.InitChatColors
import com.ai.core.utils.getCdnImageUrl
import com.ai.core.utils.ToastUtils
import com.inty.imate.R
import com.inty.imate.chat.local.db.MessageEntity
import com.inty.imate.chat.local.db.createAgentOpeningMessageEntity
import com.inty.imate.system.SystemReportEntry
import com.inty.imate.system.report.SystemReportPage
import kotlinx.serialization.Serializable

private const val ASSISTANT_LOADING_PLACEHOLDER = "loading_animation"

@Serializable
data object Chat : NavKey

@Composable
fun ChatScreen(modifier: Modifier = Modifier) {
    val viewModel: ChatViewModel = viewModel()
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    var systemReportEntry by remember { mutableStateOf<SystemReportEntry?>(null) }
    var logoutConfirmVisible by remember { mutableStateOf(false) }
    var deleteAccountConfirmVisible by remember { mutableStateOf(false) }
    val agent by viewModel.agent.collectAsStateWithLifecycle()
    val inputText by viewModel.inputText.collectAsStateWithLifecycle()
    val settingsVisible by viewModel.settingsVisible.collectAsStateWithLifecycle()
    val isLoggedIn by viewModel.isLoggedIn.collectAsStateWithLifecycle()
    val wsConnected by viewModel.isChatWebSocketConnected.collectAsStateWithLifecycle()
    val hasWsEver by viewModel.hasWebSocketConnectedAtLeastOnce.collectAsStateWithLifecycle()
    val lazyPagingItems = viewModel.messages.collectAsLazyPagingItems()

    val agentId = agent?.id?.takeIf { it.isNotBlank() }
    if (agentId == null) {
        Box(
            modifier =
                modifier
                    .fillMaxSize()
                    .background(Color(0xFF1C1523))
                    .statusBarsPadding()
                    .padding(24.dp),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = stringResource(R.string.chat_agent_missing),
                color = Color.White.copy(alpha = 0.7f),
                textAlign = TextAlign.Center,
            )
        }
        return
    }

    val companion = agent!!

    if (!wsConnected && !hasWsEver) {
        ChatWebSocketLoadingScreen(modifier = modifier.fillMaxSize())
        return
    }

    Box(
        modifier =
            modifier
                .fillMaxSize()
                .background(Color(0xFF1C1523)),
    ) {
        Column(Modifier.fillMaxSize()) {
            ChatTopBar(
                agentName = companion.name.ifBlank { stringResource(R.string.app_name) },
                avatarUrl = companion.avatar.takeIf { it.isNotBlank() }?.let { getCdnImageUrl(it) },
                onOpenSettings = { viewModel.setSettingsVisible(true) },
                modifier = Modifier.fillMaxWidth(),
            )

            val listState = rememberLazyListState()

            LazyColumn(
                state = listState,
                reverseLayout = true,
                modifier =
                    Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                item {
                    Spacer(modifier = Modifier.height(4.dp))
                }

                when (val refresh = lazyPagingItems.loadState.refresh) {
                    is LoadState.Loading ->
                        if (lazyPagingItems.itemCount == 0) {
                            item {
                                Box(
                                    modifier = Modifier.fillMaxWidth().padding(24.dp),
                                    contentAlignment = Alignment.Center,
                                ) {
                                    CircularProgressIndicator(
                                        color = InitChatColors.UserBubbleGradientEnd,
                                        strokeWidth = 2.dp,
                                        modifier = Modifier.size(28.dp),
                                    )
                                }
                            }
                        }
                    is LoadState.Error ->
                        if (lazyPagingItems.itemCount == 0) {
                            item {
                                Text(
                                    text = refresh.error.message ?: refresh.error::class.java.simpleName,
                                    color = Color.White.copy(alpha = 0.75f),
                                    modifier = Modifier.padding(16.dp),
                                )
                            }
                        }
                    else -> Unit
                }

                items(
                    count = lazyPagingItems.itemCount,
                    key = lazyPagingItems.itemKey { m -> "${m.agentId()}_${m.id}_${m.indexId}" },
                    contentType = { index ->
                        when (val m = lazyPagingItems[index]) {
                            null -> 0
                            else ->
                                when {
                                    m.role == "assistant" &&
                                        m.content == ASSISTANT_LOADING_PLACEHOLDER -> 1
                                    m.role == "user" -> 2
                                    else -> 3
                                }
                        }
                    },
                ) { index ->
                    val message = lazyPagingItems[index] ?: return@items
                    ChatMessageBubble(
                        message = message,
                        modifier = Modifier.fillMaxWidth(),
                    )
                }

                val openingLine = companion.opening.trim()
                if (openingLine.isNotEmpty()) {
                    item(key = "agent_opening_${companion.id}", contentType = 3) {
                        ChatMessageBubble(
                            message = createAgentOpeningMessageEntity(companion.id, openingLine),
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                }
            }

            ChatBottomInputBar(
                value = inputText,
                onValueChange = viewModel::onInputChange,
                placeholder = stringResource(R.string.chat_message_placeholder, companion.name.ifBlank { stringResource(R.string.app_name) }),
                onSend = { viewModel.sendMessage() },
            )
        }

        ChatSettingsBottomSheet(
            agent = companion,
            visible = settingsVisible,
            onDismiss = { viewModel.setSettingsVisible(false) },
            onSendFeedback = {
                if (!isLoggedIn) {
                    ToastUtils.showShort(R.string.system_toast_login_required_for_report)
                    return@ChatSettingsBottomSheet
                }
                viewModel.setSettingsVisible(false)
                systemReportEntry =
                    SystemReportEntry(
                        isFeedback = true,
                        targetType = "AGENT",
                        targetId = companion.id,
                    )
            },
            onReportIssue = {
                if (!isLoggedIn) {
                    ToastUtils.showShort(R.string.system_toast_login_required_for_report)
                    return@ChatSettingsBottomSheet
                }
                viewModel.setSettingsVisible(false)
                systemReportEntry =
                    SystemReportEntry(
                        isFeedback = false,
                        targetType = "AGENT",
                        targetId = companion.id,
                    )
            },
            onOpenTerms = {
                runCatching { uriHandler.openUri(context.getString(R.string.login_terms_url)) }
            },
            onOpenPrivacy = {
                runCatching { uriHandler.openUri(context.getString(R.string.login_privacy_url)) }
            },
            onLogout = {
                viewModel.setSettingsVisible(false)
                logoutConfirmVisible = true
            },
            onDeleteAccount = {
                viewModel.setSettingsVisible(false)
                deleteAccountConfirmVisible = true
            },
        )

        if (logoutConfirmVisible) {
            AlertDialog(
                onDismissRequest = { logoutConfirmVisible = false },
                title = { Text(stringResource(R.string.chat_logout_confirm_title)) },
                text = { Text(stringResource(R.string.chat_logout_confirm_message)) },
                confirmButton = {
                    TextButton(
                        onClick = {
                            logoutConfirmVisible = false
                            viewModel.logout()
                        }
                    ) {
                        Text(stringResource(R.string.chat_logout_confirm_confirm))
                    }
                },
                dismissButton = {
                    TextButton(onClick = { logoutConfirmVisible = false }) {
                        Text(stringResource(R.string.chat_delete_account_confirm_cancel))
                    }
                },
                containerColor = MaterialTheme.colorScheme.surfaceContainer
            )
        }

        if (deleteAccountConfirmVisible) {
            AlertDialog(
                onDismissRequest = { deleteAccountConfirmVisible = false },
                title = { Text(stringResource(R.string.chat_delete_account_confirm_title)) },
                text = { Text(stringResource(R.string.chat_delete_account_confirm_message)) },
                confirmButton = {
                    TextButton(
                        onClick = {
                            deleteAccountConfirmVisible = false
                            viewModel.deleteAccount()
                        }
                    ) {
                        Text(stringResource(R.string.chat_delete_account_confirm_delete))
                    }
                },
                dismissButton = {
                    TextButton(onClick = { deleteAccountConfirmVisible = false }) {
                        Text(stringResource(R.string.chat_delete_account_confirm_cancel))
                    }
                },
                containerColor = MaterialTheme.colorScheme.surfaceContainer
            )
        }

        systemReportEntry?.let { entry ->
            SystemReportPage(
                entry = entry,
                onBack = { systemReportEntry = null },
            )
        }
    }
}

@Composable
private fun ChatTopBar(
    agentName: String,
    avatarUrl: String?,
    onOpenSettings: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier =
            modifier
                .background(
                    Brush.verticalGradient(
                        colors =
                            listOf(
                                Color(0xF21E2A38),
                                Color(0x001C1523),
                            ),
                    ),
                )
                .statusBarsPadding()
                .padding(horizontal = 16.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.weight(1f),
        ) {
            Box(
                modifier =
                    Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .border(2.dp, Color(0xFFFF88B3).copy(alpha = 0.55f), CircleShape),
            ) {
                if (avatarUrl != null) {
                    AsyncImage(
                        model = avatarUrl,
                        contentDescription = stringResource(R.string.content_desc_agent_avatar),
                        modifier = Modifier.size(40.dp).clip(CircleShape),
                        contentScale = ContentScale.Crop,
                    )
                }
            }
            Column(
                modifier = Modifier.padding(start = 12.dp),
            ) {
                Text(
                    text = agentName,
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    lineHeight = 24.sp,
                )
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    Box(
                        modifier =
                            Modifier
                                .size(6.dp)
                                .clip(CircleShape)
                                .background(Color(0xFF4ADE80).copy(alpha = 0.85f)),
                    )
                    Text(
                        text = stringResource(R.string.chat_online_status),
                        color = Color.White.copy(alpha = 0.45f),
                        fontSize = 11.sp,
                        lineHeight = 16.5.sp,
                    )
                }
            }
        }

        IconButton(
            onClick = onOpenSettings,
            modifier =
                Modifier
                    .size(38.dp)
                    .background(
                        InitChatColors.TextFieldBackground,
                        CircleShape,
                    )
                    .border(1.dp, Color(0x2EC567F5), CircleShape),
        ) {
            Icon(
                imageVector = Icons.Outlined.Settings,
                contentDescription = stringResource(R.string.content_desc_settings),
                tint = Color.White,
                modifier = Modifier.size(17.dp),
            )
        }
    }
}

@Composable
private fun ChatMessageBubble(
    message: MessageEntity,
    modifier: Modifier = Modifier,
) {
    val isUser = message.role == "user"
    val isLoadingAssistant =
        message.role == "assistant" && message.content == ASSISTANT_LOADING_PLACEHOLDER
    val agentBubbleShape = RoundedCornerShape(18.dp)
    val userBubbleShape =
        RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp, bottomStart = 18.dp, bottomEnd = 4.dp)
    val typingBubbleShape =
        RoundedCornerShape(topStart = 6.dp, topEnd = 16.dp, bottomStart = 16.dp, bottomEnd = 16.dp)
    val maxWidth = 271.dp
    val isSending = isUser && message.status == MessageEntity.Status.SENDING

    Row(
        modifier =
            modifier.then(
                if (isSending) Modifier.alpha(0.79f) else Modifier,
            ),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        if (isLoadingAssistant) {
            ChatTypingIndicatorBubble(
                modifier = Modifier.widthIn(max = maxWidth),
                shape = typingBubbleShape,
            )
            return@Row
        }

        val failed = isUser && message.status == MessageEntity.Status.SENDING_FAILED
        val shape = if (isUser) userBubbleShape else agentBubbleShape
        val bubbleModifier =
            Modifier
                .widthIn(max = maxWidth)
                .then(
                    if (isUser) {
                        Modifier
                            .shadow(
                                16.dp,
                                shape,
                                ambientColor = InitChatColors.UserBubbleShadowTint,
                                spotColor = InitChatColors.UserBubbleShadowTint,
                            )
                            .clip(shape)
                            .background(
                                Brush.linearGradient(
                                    colors =
                                        listOf(
                                            InitChatColors.UserBubbleGradientStart,
                                            InitChatColors.UserBubbleGradientEnd,
                                        ),
                                    start = Offset.Zero,
                                    end = Offset(140f, 170f),
                                ),
                            )
                            .then(
                                if (failed) {
                                    Modifier.border(1.dp, MaterialTheme.colorScheme.error, shape)
                                } else {
                                    Modifier
                                },
                            )
                    } else {
                        Modifier
                            .shadow(
                                8.dp,
                                shape,
                                ambientColor = Color.Black.copy(alpha = 0.2f),
                                spotColor = Color.Black.copy(alpha = 0.2f),
                            )
                            .clip(shape)
                            .background(InitChatColors.AgentBubbleBackground)
                            .border(BorderStroke(1.dp, InitChatColors.AgentBubbleBorder), shape)
                    },
                )
                .padding(horizontal = 15.dp, vertical = 11.dp)

        Text(
            text = message.content,
            color = Color.White,
            fontSize = 14.sp,
            lineHeight = 21.7.sp,
            modifier = bubbleModifier,
        )
    }
}

@Composable
private fun ChatTypingIndicatorBubble(
    modifier: Modifier = Modifier,
    shape: RoundedCornerShape = RoundedCornerShape(16.dp),
) {
    Row(
        modifier =
            modifier
                .height(31.dp)
                .widthIn(min = 65.dp)
                .clip(shape)
                .background(InitChatColors.TypingIndicatorBackground)
                .padding(start = 16.dp, end = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box(
            Modifier
                .size(7.dp)
                .clip(CircleShape)
                .background(InitChatColors.TypingIndicatorDot.copy(alpha = 0.72f)),
        )
        Box(
            Modifier
                .size(7.dp)
                .clip(CircleShape)
                .background(InitChatColors.TypingIndicatorDot.copy(alpha = 0.52f)),
        )
        Box(
            Modifier
                .size(7.dp)
                .clip(CircleShape)
                .background(InitChatColors.TypingIndicatorDot.copy(alpha = 0.53f)),
        )
    }
}

@Composable
private fun ChatBottomInputBar(
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    onSend: () -> Unit,
) {
    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .background(InitChatColors.BottomBarBackground)
                .navigationBarsPadding()
                .imePadding(),
    ) {
        Box(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(Color.White.copy(alpha = 0.05f)),
        )
        Row(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            val pillShape = RoundedCornerShape(999.dp)
            OutlinedTextField(
                value = value,
                onValueChange = onValueChange,
                modifier = Modifier.weight(1f),
                shape = pillShape,
                placeholder = {
                    Text(
                        placeholder,
                        color = Color.White.copy(alpha = 0.45f),
                        fontSize = 14.sp,
                        lineHeight = 21.sp,
                    )
                },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { onSend() }),
                colors =
                    OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = InitChatColors.TextFieldBorder,
                        unfocusedBorderColor = InitChatColors.TextFieldBorder,
                        focusedContainerColor = InitChatColors.TextFieldBackground,
                        unfocusedContainerColor = InitChatColors.TextFieldBackground,
                        cursorColor = InitChatColors.UserBubbleGradientEnd,
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White,
                    ),
            )
            Box(
                modifier =
                    Modifier
                        .size(46.dp)
                        .clip(CircleShape)
                        .background(InitChatColors.TextFieldBackground)
                        .clickable(onClick = onSend),
                contentAlignment = Alignment.Center,
            ) {
                Icon(
                    imageVector = Icons.AutoMirrored.Outlined.Send,
                    contentDescription = stringResource(R.string.content_desc_send),
                    tint = Color.White,
                    modifier = Modifier.size(18.dp),
                )
            }
        }
    }
}
