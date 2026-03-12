package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.model.ChatMode
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.firebase.logEvent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.RadioButton
import androidx.compose.material3.RadioButtonDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.intellimate.R
import com.ai.intellimate.chat.viewmodel.ChatViewModel
import com.ai.intellimate.ui.UiConfigs
import kotlinx.coroutines.launch

/**
 * 聊天模式选择底部弹窗（Chat Mode Selector）
 *
 * 使用场景：在聊天页由用户点击「Chat Mode」后弹出，用于选择活人感 / 娱乐 / 剧情 / 怀旧等模式。 预期视觉效果：底部滑出、顶部有拖拽条与标题「Chat Mode
 * Selection」、右侧关闭按钮；主体为四个模式卡片， 每卡为标题 + 描述，右侧为单选；不展示图标与 subLabel。
 *
 * 可配置项：
 * - [onDismiss] 关闭弹窗回调
 * - [onModeSelected] 选择某一模式时回调（当前仅 UI，未接业务）
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatModeSelectorDialog(
    onDismiss: () -> Unit,
    selectedChatModeId: String? = null,
    viewModel: ChatViewModel = viewModel(),
) {
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var selectedId by remember { mutableStateOf(selectedChatModeId) }
    val chatModes by viewModel.chatModes.collectAsState()

    LaunchedEffect(Unit) { sheetState.show() }

    val colorScheme = MaterialTheme.colorScheme
    val handleHeight = dimensionResource(R.dimen.chat_mode_selector_handle_height)

    ModalBottomSheet(
        onDismissRequest = {
            scope
                .launch { sheetState.hide() }
                .invokeOnCompletion { if (!sheetState.isVisible) onDismiss() }
        },
        sheetState = sheetState,
        dragHandle = {
            Box(
                Modifier.fillMaxWidth().height(handleHeight).padding(top = UiConfigs.Spacing.Small),
                contentAlignment = Alignment.Center,
            ) {
                Box(
                    Modifier.width(32.dp)
                        .height(4.dp)
                        .clip(RoundedCornerShape(2.dp))
                        .background(colorScheme.outlineVariant)
                )
            }
        },
        containerColor = colorScheme.surfaceContainer,
        contentWindowInsets = { WindowInsets(0, 0, 0, 0) },
    ) {
        ChatModeSelectorContent(
            chatModes = chatModes,
            selectedId = selectedId,
            onModeSelected = { mode ->
                selectedId = mode.id
                FirebaseManager.Events.CHAT_MODE_SELECTOR_SELECT.logEvent(
                    "chat_mode_id" to mode.id,
                    "chat_mode_name" to mode.name,
                )
                viewModel.setChatMode(mode)
            },
            onCloseClick = {
                scope.launch {
                    sheetState.hide()
                    if (!sheetState.isVisible) onDismiss()
                }
            },
        )
    }
}

/**
 * 聊天模式选择弹窗的主体内容（标题 + 模式卡片列表）。 可在预览或非 ModalBottomSheet 容器中单独使用。
 *
 * @param chatModes 可选模式列表（来自 ViewModel / 接口）
 * @param selectedId 当前选中的模式 id，为 null 时无选中
 * @param onModeSelected 用户点击某一模式时回调
 * @param onCloseClick 用户点击关闭按钮时回调
 * @param modifier 可选修饰符
 */
@Composable
fun ChatModeSelectorContent(
    chatModes: List<ChatMode>,
    selectedId: String?,
    onModeSelected: (ChatMode) -> Unit,
    onCloseClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val colorScheme = MaterialTheme.colorScheme
    val titleBottom = dimensionResource(R.dimen.chat_mode_selector_title_bottom)
    val cardSpacing = dimensionResource(R.dimen.chat_mode_selector_card_spacing)

    Column(
        modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .background(color = MaterialTheme.colorScheme.surfaceContainer)
            .padding(bottom = UiConfigs.Padding.DialogContentVertical)
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = stringResource(R.string.chat_mode_selector_title),
                style = MaterialTheme.typography.titleMedium,
                color = colorScheme.onSurface,
                modifier = Modifier.padding(start = dimensionResource(R.dimen.padding_large)),
            )
            IconButton(onClick = onCloseClick) {
                Icon(
                    Icons.Filled.Close,
                    contentDescription =
                        stringResource(R.string.chat_mode_selector_close_content_desc),
                    tint = colorScheme.onSurface,
                )
            }
        }
        Spacer(Modifier.height(titleBottom))

        chatModes.forEachIndexed { index, mode ->
            ChatModeSelectorItem(
                title = mode.name,
                description = mode.description,
                isSelected = mode.id == selectedId,
                colorScheme = colorScheme,
                onClick = { onModeSelected(mode) },
            )
            if (index < chatModes.size - 1) {
                Spacer(Modifier.height(cardSpacing))
            }
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun PreviewChatModeSelectorContent() {
    val previewModes =
        listOf(
            ChatMode(
                "real_person",
                "Real Person Mode",
                "Dream Girl-oriented",
                "Relaxed conversation, lively and real",
            ),
            ChatMode(
                "entertainment",
                "Entertainment Mode",
                "Resonance",
                "Bracket literature, role-playing",
            ),
            ChatMode("story", "Story Mode", "Storyline", "Immersive conversation, rich storyline"),
            ChatMode(
                "nostalgia",
                "Nostalgia Mode",
                "Nostalgia",
                "Models you've chatted with before are all here~ Models you've chatted with before are all here~",
            ),
        )
    IntelliMateTheme {
        Surface(color = MaterialTheme.colorScheme.surface) {
            var selectedId by remember { mutableStateOf<String?>("real_person") }
            ChatModeSelectorContent(
                chatModes = previewModes,
                selectedId = selectedId,
                onModeSelected = { selectedId = it.id },
                onCloseClick = {},
            )
        }
    }
}

@Composable
private fun ChatModeSelectorItem(
    title: String,
    description: String,
    isSelected: Boolean,
    colorScheme: androidx.compose.material3.ColorScheme,
    onClick: () -> Unit,
) {
    val radioSize = dimensionResource(R.dimen.chat_mode_selector_radio_size)

    Surface(
        modifier =
            Modifier.fillMaxWidth().padding(horizontal = dimensionResource(R.dimen.padding_large)),
        shape = MaterialTheme.shapes.medium,
        color = colorScheme.surfaceContainerLow,
        onClick = onClick,
    ) {
        Row(
            Modifier.fillMaxWidth()
                .height(90.dp)
                .padding(horizontal = dimensionResource(R.dimen.padding_large)),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleMedium,
                    color = colorScheme.onSurface,
                )
                Spacer(Modifier.height(6.dp))
                Text(
                    text = description,
                    style = MaterialTheme.typography.bodySmall,
                    color = colorScheme.onSurfaceVariant,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
            RadioButton(
                selected = isSelected,
                onClick = onClick,
                modifier = Modifier.size(radioSize),
                colors =
                    RadioButtonDefaults.colors(
                        selectedColor = colorScheme.primary,
                        unselectedColor = colorScheme.outline,
                    ),
            )
        }
    }
}
