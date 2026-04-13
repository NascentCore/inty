package com.inty.imate.chat

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation3.runtime.NavKey
import coil3.compose.AsyncImage
import com.ai.core.utils.getCdnImageUrl
import com.ai.core.ui.theme.InitChatColors
import com.inty.imate.R
import kotlinx.serialization.Serializable

@Serializable
data object InitChat: NavKey

@Composable
fun InitChatRoute(
    modifier: Modifier = Modifier,
    viewModel: InitChatViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    InitChatScreen(
        uiState = uiState,
        onInputTextChanged = viewModel::onInputTextChanged,
        onSubmit = {
            when (uiState.step) {
                InitChatStep.Name -> viewModel.submitName()
                InitChatStep.Appearance -> viewModel.submitAppearance()
                else -> Unit
            }
        },
        onGenderSelected = viewModel::selectGender,
        onConfirmEnterChat = viewModel::confirmEnterChat,
        modifier = modifier,
    )
}

@Composable
fun InitChatScreen(
    uiState: InitChatUiState,
    onInputTextChanged: (String) -> Unit,
    onSubmit: () -> Unit,
    onGenderSelected: (InitChatGender) -> Unit,
    onConfirmEnterChat: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val listState = rememberLazyListState()
    LaunchedEffect(uiState.messages.size) {
        if (uiState.messages.isNotEmpty()) {
            listState.animateScrollToItem(uiState.messages.lastIndex)
        }
    }

    Column(
        modifier =
            modifier
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.background),
    ) {
        InitChatHeader(
            step = uiState.step,
            progress = uiState.progress,
            title = uiState.headerTitle,
            subtitle = uiState.headerSubtitle,
            avatarUrl = uiState.avatarUrl,
        )

        LazyColumn(
            state = listState,
            modifier =
                Modifier
                    .weight(1f, fill = true)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
                    .padding(top = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            items(
                count = uiState.messages.size,
                key = { idx -> uiState.messages[idx].id },
            ) { idx ->
                val msg = uiState.messages[idx]
                InitChatBubble(message = msg)
            }
            item(key = "bottom_spacer") { Spacer(Modifier.height(12.dp)) }
        }

        InitChatBottomBar(
            uiState = uiState,
            onInputTextChanged = onInputTextChanged,
            onSubmit = onSubmit,
            onGenderSelected = onGenderSelected,
            onConfirmEnterChat = onConfirmEnterChat,
        )
    }
}

@Composable
private fun InitChatHeader(
    step: InitChatStep,
    progress: Float,
    title: InitChatMessageText,
    subtitle: InitChatMessageText,
    avatarUrl: String?,
) {
    val headerBg =
        when (step) {
            InitChatStep.Name -> InitChatColors.HeaderBgName
            InitChatStep.Gender -> InitChatColors.HeaderBgGender
            InitChatStep.Appearance -> InitChatColors.HeaderBgAppearance
            InitChatStep.Generating -> InitChatColors.HeaderBgGenerating
            InitChatStep.Done -> InitChatColors.HeaderBgDone
        }

    val animatedProgress by animateFloatAsState(
        targetValue = progress.coerceIn(0f, 1f),
        animationSpec = tween(durationMillis = 550, easing = FastOutSlowInEasing),
        label = "initChatHeaderProgress",
    )

    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .background(headerBg),
    ) {
        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .statusBarsPadding()
                    .padding(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                InitChatHeaderAvatar(avatarUrl = avatarUrl)
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = resolveText(title),
                        color = Color.White,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(Modifier.height(2.dp))
                    Text(
                        text = resolveText(subtitle),
                        color = Color.White.copy(alpha = 0.5f),
                        fontSize = 11.sp,
                    )
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = stringResourceCompat(R.string.init_chat_profile_completion_label),
                    color = Color.White.copy(alpha = 0.5f),
                    fontSize = 11.sp,
                    letterSpacing = 0.44.sp,
                )
                Spacer(Modifier.weight(1f))
                Text(
                    text = "${(animatedProgress * 100).toInt()}%",
                    color = InitChatColors.UserBubbleGradientEnd,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            }

            InitChatProgressBar(progress = animatedProgress)
        }
    }
}

@Composable
private fun InitChatHeaderAvatar(avatarUrl: String?) {
    val shape = CircleShape
    val baseModifier =
        Modifier
            .size(44.dp)
            .clip(shape)
            .border(2.dp, InitChatColors.UserBubbleGradientStart.copy(alpha = 0.52f), shape)

    if (avatarUrl.isNullOrBlank()) {
        Box(
            modifier =
                baseModifier.background(
                    Brush.radialGradient(
                        colors = listOf(InitChatColors.UserBubbleGradientStart, Color(0xFF1E2A38)),
                    ),
                ),
        )
        return
    }

    AsyncImage(
        model = getCdnImageUrl(avatarUrl, width = 128, quality = 75) ?: avatarUrl,
        contentDescription = null,
        contentScale = ContentScale.Crop,
        modifier = baseModifier,
    )
}

@Composable
private fun InitChatProgressBar(progress: Float) {
    val shape = RoundedCornerShape(999.dp)
    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(4.dp)
                .clip(shape)
                .background(InitChatColors.ProgressTrack),
    ) {
        Box(
            modifier =
                Modifier
                    .fillMaxWidth(fraction = progress.coerceIn(0f, 1f))
                    .height(4.dp)
                    .clip(shape)
                    .background(
                        Brush.horizontalGradient(
                            colors =
                                listOf(
                                    InitChatColors.UserBubbleGradientStart,
                                    InitChatColors.UserBubbleGradientEnd,
                                    Color(0xFFC3F0FD),
                                ),
                        ),
                    ),
        )
    }
}

@Composable
private fun InitChatBubble(message: InitChatMessage) {
    var revealed by remember(message.id) { mutableStateOf(false) }
    LaunchedEffect(message.id) { revealed = true }
    val enterAlpha by animateFloatAsState(
        targetValue = if (revealed) 1f else 0f,
        animationSpec = tween(durationMillis = 320, easing = FastOutSlowInEasing),
        label = "initChatBubbleAlpha",
    )
    val offsetY by animateFloatAsState(
        targetValue = if (revealed) 0f else 14f,
        animationSpec = tween(durationMillis = 320, easing = FastOutSlowInEasing),
        label = "initChatBubbleOffsetY",
    )

    val isAgent = message.role == InitChatRole.Agent
    val bubbleShape = RoundedCornerShape(18.dp)
    val maxWidth = 271.dp

    Row(
        modifier =
            Modifier
                .fillMaxWidth()
                .graphicsLayer {
                    alpha = enterAlpha
                    translationY = offsetY
                },
        horizontalArrangement = if (isAgent) Arrangement.Start else Arrangement.End,
    ) {
        val bubbleModifier =
            Modifier
                .widthIn(max = maxWidth)
                .clip(bubbleShape)
                .then(
                    if (isAgent) {
                        Modifier
                            .background(InitChatColors.AgentBubbleBackground)
                            .border(BorderStroke(1.dp, InitChatColors.AgentBubbleBorder), bubbleShape)
                    } else {
                        Modifier
                            .shadow(16.dp, bubbleShape, ambientColor = InitChatColors.UserBubbleGradientStart.copy(alpha = 0.25f), spotColor = InitChatColors.UserBubbleGradientStart.copy(alpha = 0.25f))
                            .background(
                                Brush.linearGradient(
                                    colors = listOf(InitChatColors.UserBubbleGradientStart, InitChatColors.UserBubbleGradientEnd),
                                ),
                            )
                    },
                )
                .padding(horizontal = 17.dp, vertical = 13.dp)

        Text(
            text = resolveText(message.text),
            color = Color.White,
            fontSize = 14.sp,
            lineHeight = 21.7.sp,
            modifier = bubbleModifier,
        )
    }
}

@Composable
private fun InitChatBottomBar(
    uiState: InitChatUiState,
    onInputTextChanged: (String) -> Unit,
    onSubmit: () -> Unit,
    onGenderSelected: (InitChatGender) -> Unit,
    onConfirmEnterChat: () -> Unit,
) {
    Column(
        modifier =
            Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .imePadding(),
    ) {
        Box(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(InitChatColors.Divider),
        )
        Column(
            modifier =
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 13.dp),
        ) {
            when (uiState.step) {
                InitChatStep.Name -> {
                    InitChatTextInputRow(
                        value = uiState.inputText,
                        placeholder = stringResourceCompat(R.string.init_chat_placeholder_name),
                        onValueChange = onInputTextChanged,
                        onSubmit = onSubmit,
                    )
                }

                InitChatStep.Appearance -> {
                    InitChatTextInputRow(
                        value = uiState.inputText,
                        placeholder = stringResourceCompat(R.string.init_chat_placeholder_appearance),
                        onValueChange = onInputTextChanged,
                        onSubmit = onSubmit,
                    )
                }

                InitChatStep.Gender -> {
                    InitChatGenderRow(onGenderSelected = onGenderSelected)
                }

                InitChatStep.Generating -> {
                    InitChatGeneratingRow()
                }

                InitChatStep.Done -> {
                    InitChatBeginButton(enabled = uiState.doneEnabled, onClick = onConfirmEnterChat)
                }
            }
        }
    }
}

@Composable
private fun InitChatTextInputRow(
    value: String,
    placeholder: String,
    onValueChange: (String) -> Unit,
    onSubmit: () -> Unit,
) {
    val textFieldShape = RoundedCornerShape(999.dp)

    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.weight(1f),
            shape = textFieldShape,
            placeholder = { Text(placeholder, color = Color.White.copy(alpha = 0.6f), fontSize = 14.sp) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
            keyboardActions = KeyboardActions(onSend = { onSubmit() }),
            colors =
                androidx.compose.material3.OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = InitChatColors.TextFieldBorder,
                    unfocusedBorderColor = InitChatColors.TextFieldBorder,
                    focusedContainerColor = InitChatColors.TextFieldBackground,
                    unfocusedContainerColor = InitChatColors.TextFieldBackground,
                    cursorColor = Color.White,
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
                    .clickable(onClick = onSubmit)
                    .padding(14.dp),
            contentAlignment = Alignment.Center,
        ) {
            androidx.compose.material3.Icon(
                imageVector = Icons.AutoMirrored.Filled.Send,
                contentDescription = stringResourceCompat(R.string.content_desc_send),
                tint = Color.White.copy(alpha = 0.9f),
            )
        }
    }
}

@Composable
private fun InitChatGenderRow(onGenderSelected: (InitChatGender) -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        InitChatGenderCard(
            modifier = Modifier.weight(1f),
            emoji = "💙",
            label = stringResourceCompat(R.string.init_chat_gender_male),
            accent = InitChatColors.GenderMaleAccent,
            background = InitChatColors.GenderMaleBackground,
            onClick = { onGenderSelected(InitChatGender.Male) },
        )
        InitChatGenderCard(
            modifier = Modifier.weight(1f),
            emoji = "💗",
            label = stringResourceCompat(R.string.init_chat_gender_female),
            accent = InitChatColors.GenderFemaleAccent,
            background = InitChatColors.GenderFemaleBackground,
            onClick = { onGenderSelected(InitChatGender.Female) },
        )
        InitChatGenderCard(
            modifier = Modifier.weight(1f),
            emoji = "💙",
            label = stringResourceCompat(R.string.init_chat_gender_no_pref),
            accent = InitChatColors.GenderNoPrefAccent,
            background = InitChatColors.GenderNoPrefBackground,
            onClick = { onGenderSelected(InitChatGender.NoPref) },
        )
    }
}

@Composable
private fun InitChatGenderCard(
    modifier: Modifier,
    emoji: String,
    label: String,
    accent: Color,
    background: Color,
    onClick: () -> Unit,
) {
    val shape = RoundedCornerShape(16.dp)
    Column(
        modifier =
            modifier
                .height(83.dp)
                .clip(shape)
                .background(background)
                .border(BorderStroke(1.5.dp, accent), shape)
                .clickable(onClick = onClick)
                .padding(vertical = 14.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(text = emoji, fontSize = 22.sp)
        Text(text = label, color = accent, fontSize = 13.sp, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun InitChatGeneratingRow() {
    Row(
        modifier = Modifier.fillMaxWidth().height(51.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Box(Modifier.size(10.dp).clip(CircleShape).background(InitChatColors.UserBubbleGradientStart.copy(alpha = 0.86f)))
        Spacer(Modifier.width(12.dp))
        Text(
            text = stringResourceCompat(R.string.init_chat_generating_footer),
            color = InitChatColors.UserBubbleGradientStart.copy(alpha = 0.9f),
            fontSize = 13.sp,
        )
        Spacer(Modifier.width(12.dp))
        Box(Modifier.size(12.dp).clip(CircleShape).background(InitChatColors.UserBubbleGradientEnd.copy(alpha = 0.51f)))
    }
}

@Composable
private fun InitChatBeginButton(enabled: Boolean, onClick: () -> Unit) {
    val shape = RoundedCornerShape(999.dp)
    val brush =
        Brush.linearGradient(
            colors = listOf(InitChatColors.UserBubbleGradientStart, InitChatColors.UserBubbleGradientEnd),
        )

    Box(
        modifier =
            Modifier
                .fillMaxWidth()
                .height(56.dp)
                .clip(shape)
                .background(brush)
                .shadow(32.dp, shape, ambientColor = InitChatColors.UserBubbleGradientStart.copy(alpha = 0.45f), spotColor = InitChatColors.UserBubbleGradientStart.copy(alpha = 0.45f))
                .clickable(enabled = enabled, onClick = onClick)
                .padding(vertical = 16.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            text = stringResourceCompat(R.string.init_chat_cta_begin),
            color = Color.White,
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.32.sp,
        )
    }
}

@Composable
private fun resolveText(text: InitChatMessageText): String =
    when (text) {
        is InitChatMessageText.Plain -> text.text
        is InitChatMessageText.Res -> stringResourceCompat(text.id, text.args)
        is InitChatMessageText.Parts ->
            buildString {
                text.parts.forEach { append(resolveText(it)) }
            }
    }

@Composable
private fun stringResourceCompat(id: Int, args: List<String> = emptyList()): String {
    val raw = androidx.compose.ui.res.stringResource(id)
    return if (args.isEmpty()) raw else String.format(raw, *args.toTypedArray())
}

