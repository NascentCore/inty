package com.ai.intellimate.ui

import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
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
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.TextRange
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.TextFieldValue
import com.ai.intellimate.R
import kotlinx.coroutines.launch

@Composable
fun IntySmallTextField(
    modifier: Modifier = Modifier,
    value: String,
    singleLine: Boolean = false,
    enabled: Boolean = true,
    placeholder: @Composable (() -> Unit)? = null,
    leadingIcon: @Composable (() -> Unit)? = null,
    trailingIcon: @Composable (() -> Unit)? = null,
    keyboardOptions: KeyboardOptions =
        KeyboardOptions(
            imeAction = ImeAction.Done,
            // 每个单词都大写
            capitalization = KeyboardCapitalization.Words,
        ),
    keyboardActions: KeyboardActions = KeyboardActions.Default,
    onValueChange: (String) -> Unit,
    onFocusChanged: ((Boolean) -> Unit)? = null,
    onSelectionChanged: ((Int) -> Unit)? = null,
    selection: Int = 0,
    maxLines: Int = Int.MAX_VALUE,
    maxLength: Int = UiConfigs.Limits.DefaultTextFieldMaxChars, // 输入文案默认最大1000个字符
    focusRequester: FocusRequester? = null,
) {

    Row(modifier = modifier.wrapContentHeight(), verticalAlignment = Alignment.CenterVertically) {
        leadingIcon?.let { it() }

        val focusManager = LocalFocusManager.current

        val newActions =
            KeyboardActions(
                onDone = {
                    focusManager.clearFocus()
                    keyboardActions.onDone?.let { it() }
                },
                onGo = {
                    focusManager.clearFocus()
                    keyboardActions.onGo?.let { it() }
                },
                onNext = {
                    focusManager.clearFocus()
                    keyboardActions.onNext?.let { it() }
                },
                onPrevious = {
                    focusManager.clearFocus()
                    keyboardActions.onPrevious?.let { it() }
                },
                onSearch = {
                    focusManager.clearFocus()
                    keyboardActions.onSearch?.let { it() }
                },
                onSend = {
                    focusManager.clearFocus()
                    keyboardActions.onSend?.let { it() }
                },
            )

        Box(
            modifier = Modifier.weight(1f),
            contentAlignment = if (singleLine) Alignment.CenterStart else Alignment.TopStart,
        ) {
            var textFieldValue by remember {
                mutableStateOf(
                    TextFieldValue(
                        value,
                        selection = TextRange(selection.coerceAtMost(value.length)),
                    )
                )
            }

            // 使用LaunchedEffect来监听外部value和selection的变化
            LaunchedEffect(value, selection) {
                textFieldValue =
                    textFieldValue.copy(
                        text = value,
                        selection = TextRange(selection.coerceAtMost(value.length)),
                    )
            }
            val scope = rememberCoroutineScope()
            val textFieldModifier =
                Modifier.fillMaxWidth()
                    .onFocusChanged { focusState -> onFocusChanged?.invoke(focusState.isFocused) }
                    .let { modifierWithFocus ->
                        focusRequester?.let { modifierWithFocus.focusRequester(it) }
                            ?: modifierWithFocus
                    }

            TextField(
                modifier = textFieldModifier,
                enabled = enabled,
                singleLine = singleLine,
                value = textFieldValue,
                onValueChange = { newValue ->
                    // 1. 检查长度限制
                    val isOverLength = maxLength > 0 && newValue.text.length > maxLength

                    val finalValue = if (isOverLength) {
                        // 仅在首次超过时提示（建议加防抖，避免连续粘贴产生的多次 Toast）
                        scope.launch { ToastUtils.showShort(R.string.str_message_is_too_long) }

                        // 截断文字，同时必须保留 composition 和 selection 的合法性
                        val truncatedText = newValue.text.take(maxLength)
                        newValue.copy(
                            text = truncatedText,
                            selection = TextRange(newValue.selection.start.coerceAtMost(maxLength)),
                            composition = newValue.composition?.let {
                                TextRange(it.start.coerceAtMost(maxLength), it.end.coerceAtMost(maxLength))
                            }
                        )
                    } else {
                        newValue
                    }

                    // 2. 关键：直接使用 newValue 的整体或 copy，不要手动 new 丢掉 composition
                    textFieldValue = finalValue

                    // 3. 外部回调
                    onValueChange(finalValue.text)
                    onSelectionChanged?.invoke(finalValue.selection.start)
                },
                keyboardOptions = keyboardOptions,
                keyboardActions = newActions,
                textStyle =
                    TextStyle.Default.copy(
                        fontSize = UiConfigs.Typography.Body,
                        color = Color.White,
                    ),
                colors =
                    TextFieldDefaults.colors(
                        focusedContainerColor = Color.Transparent,
                        unfocusedContainerColor = Color.Transparent,
                        disabledContainerColor = Color.Transparent,
                        focusedIndicatorColor = Color.Transparent,
                        unfocusedIndicatorColor = Color.Transparent,
                        disabledIndicatorColor = Color.Transparent,
                        cursorColor = Color.White,
                    ),
                placeholder = placeholder,
                maxLines = maxLines,
            )
        }

        trailingIcon?.let { it() }
    }
}

@Composable
fun IntySmallTextField2(
    modifier: Modifier = Modifier,
    value: String,
    singleLine: Boolean = false,
    enabled: Boolean = true,
    maxLength: Int = UiConfigs.Limits.DefaultTextFieldMaxChars, // 限制最大输入字数，-1 表示不限制
    placeholder: @Composable (() -> Unit)? = null,
    leadingIcon: @Composable (() -> Unit)? = null,
    trailingIcon: @Composable (() -> Unit)? = null,
    keyboardOptions: KeyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
    keyboardActions: KeyboardActions = KeyboardActions.Default,
    onValueChange: (String) -> Unit,
) {

    Row(modifier = modifier.fillMaxHeight(), verticalAlignment = Alignment.CenterVertically) {
        leadingIcon?.let { it() }

        val focusManager = LocalFocusManager.current

        val newActions =
            KeyboardActions(
                onDone = {
                    focusManager.clearFocus()
                    keyboardActions.onDone?.let { it() }
                },
                onGo = {
                    focusManager.clearFocus()
                    keyboardActions.onGo?.let { it() }
                },
                onNext = {
                    focusManager.clearFocus()
                    keyboardActions.onNext?.let { it() }
                },
                onPrevious = {
                    focusManager.clearFocus()
                    keyboardActions.onPrevious?.let { it() }
                },
                onSearch = {
                    focusManager.clearFocus()
                    keyboardActions.onSearch?.let { it() }
                },
                onSend = {
                    focusManager.clearFocus()
                    keyboardActions.onSend?.let { it() }
                },
            )

        Box(
            modifier =
                Modifier.fillMaxHeight()
                    .weight(1f)
                    .padding(
                        horizontal = UiConfigs.Padding.TextFieldHorizontal,
                        vertical = UiConfigs.Padding.TextFieldVertical,
                    ),
            contentAlignment = if (singleLine) Alignment.CenterStart else Alignment.TopStart,
        ) {
            BasicTextField(
                modifier = Modifier.fillMaxWidth(),
                enabled = enabled,
                singleLine = singleLine,
                value = value,
                textStyle =
                    TextStyle.Default.copy(
                        fontSize = UiConfigs.Typography.Body,
                        color = Color.White,
                    ),
                onValueChange = { str ->
                    // 有最大输入数字限制时候
                    if (maxLength > 0 && str.length <= maxLength) {
                        onValueChange(str)
                    } else {
                        // 不作限制
                        if (maxLength == -1) {
                            onValueChange(str)
                        }
                    }
                },
                keyboardOptions = keyboardOptions,
                keyboardActions = newActions,
                cursorBrush = SolidColor(Color.White),
            )
            if (value.isEmpty()) {
                placeholder?.let { it() }
            }
        }
        trailingIcon?.let { it() }
    }
}
