package ai.sxwl.android.design.ui

import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import kotlinx.coroutines.yield

/**
 * 面板配置接口
 * 每个面板需要实现此接口以提供面板内容和标识
 */
interface PanelConfig {
    /** 面板唯一标识符 */
    val id: String
    
    /** 面板显示名称（可选，用于调试） */
    val name: String
    
    /** 面板内容 */
    @Composable
    fun PanelContent(
        modifier: Modifier,
        onDismiss: () -> Unit,
        onItemSelected: (Any) -> Unit,
    )
}

/**
 * 面板按钮配置
 * 
 * @param panelConfig 面板配置（可选，如果为null则作为普通按钮使用）
 * @param icon 按钮图标（Composable）
 * @param isVisible 是否显示此按钮
 * @param onClick 点击回调（如果panelConfig不为null且onClick为null，则默认会切换面板）
 */
data class PanelButtonConfig(
    val panelConfig: PanelConfig?,
    val icon: @Composable () -> Unit,
    val isVisible: Boolean = true,
    val onClick: (() -> Unit)? = null,
)

/**
 * 输入框配置
 */
data class InputFieldConfig(
    val placeholder: String = "",
    val maxLines: Int = 4,
    val maxLength: Int = 500,
    val textStyle: TextStyle = TextStyle(
        fontSize = 14.sp,
        color = Color.White,
    ),
    val keyboardOptions: androidx.compose.foundation.text.KeyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
        imeAction = ImeAction.Default,
        capitalization = KeyboardCapitalization.Sentences,
    ),
)

/**
 * 输入框容器配置
 */
data class InputContainerConfig(
    val backgroundColor: Color = Color(0x9937303D),
    val cornerRadius: Dp = 12.dp,
    val horizontalPadding: Dp = 16.dp,
    val topPadding: Dp = 12.dp,
    val bottomPadding: Dp = 12.dp,
    val minHeight: Dp = 48.dp,
    val maxHeight: Dp = 120.dp,
)

/**
 * 面板容器配置
 */
data class PanelContainerConfig(
    val backgroundColor: Color = Color(0xFF1C1523),
    val cornerRadius: Dp = 0.dp,
    val horizontalPadding: Dp = 16.dp,
    val topPadding: Dp = 24.dp,
    val bottomPadding: Dp = 32.dp,
    val animationDuration: Int = 300,
)

/**
 * 多面板输入框组件
 * 
 * 这是一个通用的输入框组件，支持多个功能面板（如表情包、礼物背包等）。
 * 输入框和功能面板作为一个整体，当键盘显示或功能面板显示时，输入框会自动上移。
 * 功能面板的高度会匹配键盘高度，确保切换时无跳动。
 * 
 * @param value 输入框文本值
 * @param onValueChange 文本变化回调
 * @param panelButtons 面板按钮配置列表
 * @param onSendMessage 发送消息回调（当输入框有内容时，右侧按钮变为发送按钮）
 * @param onPanelItemSelected 面板项选择回调
 * @param modifier 修饰符
 * @param inputFieldConfig 输入框配置
 * @param inputContainerConfig 输入框容器配置
 * @param panelContainerConfig 面板容器配置
 * @param focusRequester 焦点请求器（可选）
 * @param onFocusChange 焦点变化回调
 * @param onPanelVisibilityChange 面板显示状态变化回调（panelId: String?），null表示面板关闭
 * @param externalPanelId 外部控制的面板ID（可选），用于外部控制面板显示/隐藏，设置为null可关闭面板
 * @param bottomPadding 底部内边距（用于适配系统导航栏）
 * @param windowInsets 窗口内边距（默认使用导航栏）
 */
@Composable
fun MultiPanelInputField(
    value: String,
    onValueChange: (String) -> Unit,
    panelButtons: List<PanelButtonConfig>,
    onSendMessage: () -> Unit,
    onPanelItemSelected: (String, Any) -> Unit,
    modifier: Modifier = Modifier,
    inputFieldConfig: InputFieldConfig = InputFieldConfig(),
    inputContainerConfig: InputContainerConfig = InputContainerConfig(),
    panelContainerConfig: PanelContainerConfig = PanelContainerConfig(),
    focusRequester: FocusRequester? = null,
    onFocusChange: (Boolean) -> Unit = {},
    onPanelVisibilityChange: ((String?) -> Unit)? = null,
    externalPanelId: String? = null,
    bottomPadding: Dp = 0.dp,
    windowInsets: WindowInsets = WindowInsets.navigationBars,
) {
    val density = LocalDensity.current
    val keyboardController = LocalSoftwareKeyboardController.current
    val scope = rememberCoroutineScope()
    
    // 当前显示的面板ID，null表示没有面板显示
    var currentPanelId by remember { mutableStateOf<String?>(null) }
    
    // 同步外部控制的面板ID
    LaunchedEffect(externalPanelId) {
        if (externalPanelId != currentPanelId) {
            currentPanelId = externalPanelId
        }
    }
    
    // 键盘高度
    val imeBottom = WindowInsets.ime.getBottom(density)
    val isKeyboardVisible = imeBottom > 0
    val keyboardHeightDp = with(density) { imeBottom.toDp() }
    
    // 通知外部面板状态变化
    LaunchedEffect(currentPanelId) {
        onPanelVisibilityChange?.invoke(currentPanelId)
    }
    
    // 当键盘显示时，隐藏面板；当面板显示时，隐藏键盘
    LaunchedEffect(isKeyboardVisible) {
        if (isKeyboardVisible && currentPanelId != null) {
            // 键盘显示时，关闭面板
            currentPanelId = null
        }
    }
    
    // 切换面板
    fun togglePanel(panelId: String) {
        if (currentPanelId == panelId) {
            // 关闭当前面板，不弹出键盘
            currentPanelId = null
        } else {
            // 打开新面板，直接显示，不做动画
            // 先隐藏键盘
            keyboardController?.hide()
            // 直接设置面板ID，立即显示
            currentPanelId = panelId
        }
    }
    
    // 关闭面板
    fun dismissPanel() {
        currentPanelId = null
    }
    
    // 焦点输入框并显示键盘
    fun focusInputAndShowKeyboard() {
        focusRequester?.requestFocus()
        scope.launch {
            yield()
            keyboardController?.show()
        }
    }
    
    // 输入框和面板整体容器
    Column(
        modifier = modifier
            .windowInsetsPadding(WindowInsets.ime)
            .windowInsetsPadding(windowInsets)
    ) {
        // 输入框容器
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(
                    start = inputContainerConfig.horizontalPadding,
                    top = inputContainerConfig.topPadding,
                    end = inputContainerConfig.horizontalPadding,
                    bottom = inputContainerConfig.bottomPadding,
                )
                .clip(RoundedCornerShape(inputContainerConfig.cornerRadius))
                .background(inputContainerConfig.backgroundColor)
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(
                        min = inputContainerConfig.minHeight,
                        max = inputContainerConfig.maxHeight
                    )
            ) {
                // 输入框
                TextField(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(end = 56.dp) // 为右侧按钮留出空间
                        .onFocusChanged { 
                            onFocusChange(it.isFocused)
                            // 当输入框获得焦点时，如果面板正在显示，关闭面板
                            if (it.isFocused && currentPanelId != null) {
                                currentPanelId = null
                            }
                        }
                        .let { mod ->
                            focusRequester?.let { mod.focusRequester(it) } ?: mod
                        },
                    value = value,
                    onValueChange = { newValue ->
                        if (newValue.length <= inputFieldConfig.maxLength) {
                            onValueChange(newValue)
                        }
                    },
                    placeholder = {
                        if (inputFieldConfig.placeholder.isNotEmpty()) {
                            Text(
                                text = inputFieldConfig.placeholder,
                                style = inputFieldConfig.textStyle.copy(
                                    color = Color.White.copy(alpha = 0.5f)
                                )
                            )
                        }
                    },
                    textStyle = inputFieldConfig.textStyle,
                    keyboardOptions = inputFieldConfig.keyboardOptions,
                    keyboardActions = KeyboardActions(),
                    maxLines = inputFieldConfig.maxLines,
                    colors = TextFieldDefaults.colors(
                        focusedContainerColor = Color.Transparent,
                        unfocusedContainerColor = Color.Transparent,
                        disabledContainerColor = Color.Transparent,
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent,
                        disabledIndicatorColor = Color.Transparent,
                        cursorColor = Color.White,
                    ),
                )
                
                // 右侧按钮区域
                Row(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .padding(end = 12.dp, bottom = 8.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.Bottom,
                ) {
                    // 根据输入内容显示不同按钮
                    if (value.isEmpty()) {
                        // 没有输入内容时，显示面板按钮
                        panelButtons.forEach { buttonConfig ->
                            if (buttonConfig.isVisible && buttonConfig.panelConfig != null) {
                                Box(
                                    modifier = Modifier
                                        .size(32.dp)
                                        .noRippleClickable {
                                            buttonConfig.onClick?.invoke() ?: run {
                                                togglePanel(buttonConfig.panelConfig!!.id)
                                            }
                                        }
                                ) {
                                    buttonConfig.icon()
                                }
                            }
                        }
                    } else {
                        // 有输入内容时，显示发送按钮
                        // 发送按钮应该是 panelConfig 为 null 的按钮
                        val sendButton = panelButtons.firstOrNull { it.panelConfig == null }
                        if (sendButton != null && sendButton.isVisible) {
                            Box(
                                modifier = Modifier
                                    .size(32.dp)
                                    .noRippleClickable {
                                        sendButton.onClick?.invoke() ?: onSendMessage()
                                    }
                            ) {
                                sendButton.icon()
                            }
                        }
                    }
                }
            }
        }
        
        // 功能面板（显示在输入框下方）
        // 直接显示，不做动画
        if (currentPanelId != null && !isKeyboardVisible) {
            val currentPanel = panelButtons
                .firstOrNull { it.panelConfig?.id == currentPanelId }
                ?.panelConfig
            
            if (currentPanel != null) {
                // 面板高度应该匹配键盘高度，如果没有键盘高度，使用默认高度
                val panelHeight = if (keyboardHeightDp > 0.dp) {
                    keyboardHeightDp
                } else {
                    // 默认面板高度（通常和键盘高度相近）
                    300.dp
                }
                
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(panelHeight)
                        .background(
                            color = panelContainerConfig.backgroundColor,
                            shape = RoundedCornerShape(
                                topStart = panelContainerConfig.cornerRadius,
                                topEnd = panelContainerConfig.cornerRadius,
                            )
                        )
                        .padding(
                            start = panelContainerConfig.horizontalPadding,
                            top = panelContainerConfig.topPadding,
                            end = panelContainerConfig.horizontalPadding,
                            bottom = panelContainerConfig.bottomPadding,
                        ),
                ) {
                    currentPanel.PanelContent(
                        modifier = Modifier.fillMaxWidth(),
                        onDismiss = { dismissPanel() },
                        onItemSelected = { item ->
                            onPanelItemSelected(currentPanel.id, item)
                        },
                    )
                }
            }
        }
    }
}
