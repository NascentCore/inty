package com.ai.inty.base

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.TextField
import androidx.compose.material3.TextFieldDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.ui.theme.TextFieldColor


@Composable
fun IntySmallTextField(
    modifier: Modifier = Modifier,
    value: String,
    isError: Boolean = false,
    singleLine: Boolean = false,
    enabled: Boolean = true,
    placeholder: @Composable (() -> Unit)? = null,
    leadingIcon: @Composable (() -> Unit)? = null,
    trailingIcon: @Composable (() -> Unit)? = null,
    keyboardOptions: KeyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
    keyboardActions: KeyboardActions = KeyboardActions.Default,
    onValueChange: (String) -> Unit,
    onFocusChanged: ((Boolean) -> Unit)? = null,
    onSelectionChanged: ((Int) -> Unit)? = null,
    selection: Int = 0,
) {

    Row(
        modifier = modifier
            .fillMaxHeight()
        ,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        leadingIcon?.let { it() }
        Spacer(modifier = Modifier.width(19.dp))
//        DividerRow(
//            modifier = Modifier.height(19.dp),
//            color = Color(0xff9f9f9f), thickness = 1.dp
//        )
        Spacer(modifier = Modifier.width(7.dp))

        val focusManager = LocalFocusManager.current

        val newActions = KeyboardActions(
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
            modifier = Modifier
                .weight(1f),
            contentAlignment = if (singleLine) Alignment.CenterStart else Alignment.TopStart,
        ) {
            var textFieldValue by remember { mutableStateOf(TextFieldValue(value, selection = androidx.compose.ui.text.TextRange(selection))) }
            
            // 当外部value或selection变化时，更新TextFieldValue
            if (textFieldValue.text != value || textFieldValue.selection.start != selection) {
                textFieldValue = textFieldValue.copy(
                    text = value,
                    selection = androidx.compose.ui.text.TextRange(selection)
                )
            }
            
            TextField(
                modifier = Modifier
                    .fillMaxWidth()
                    .onFocusChanged { focusState ->
                        onFocusChanged?.invoke(focusState.isFocused)
                    },
                enabled = enabled,
                singleLine = singleLine,
                value = textFieldValue,
                onValueChange = { newValue ->
                    textFieldValue = newValue
                    onValueChange(newValue.text)
                    onSelectionChanged?.invoke(newValue.selection.start)
                },
                keyboardOptions = keyboardOptions,
                keyboardActions = newActions,
                textStyle = TextStyle.Default.copy(
                    fontSize = 14.sp,
                    color = TextFieldColor.Text
                ),
                colors = TextFieldDefaults.colors(
                    focusedContainerColor = androidx.compose.ui.graphics.Color.Transparent,
                    unfocusedContainerColor = androidx.compose.ui.graphics.Color.Transparent,
                    disabledContainerColor = androidx.compose.ui.graphics.Color.Transparent,
                    focusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent,
                    unfocusedIndicatorColor = androidx.compose.ui.graphics.Color.Transparent,
                    disabledIndicatorColor = androidx.compose.ui.graphics.Color.Transparent,
                    cursorColor = TextFieldColor.Text
                ),
                placeholder = placeholder
            )
        }


        trailingIcon?.let { it() }

        Spacer(modifier = Modifier.width(10.dp))

    }
}

@Composable
fun IntySmallTextField2(
    modifier: Modifier = Modifier,
    value: String,
    isError: Boolean = false,
    singleLine: Boolean = false,
    enabled: Boolean = true,
    placeholder: @Composable (() -> Unit)? = null,
    leadingIcon: @Composable (() -> Unit)? = null,
    trailingIcon: @Composable (() -> Unit)? = null,
    keyboardOptions: KeyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
    keyboardActions: KeyboardActions = KeyboardActions.Default,
    onValueChange: (String) -> Unit,
) {

    Row(
        modifier = modifier
            .fillMaxHeight()
        ,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        leadingIcon?.let { it() }
//        Spacer(modifier = Modifier.width(19.dp))
//        DividerRow(
//            modifier = Modifier.height(19.dp),
//            color = Color(0xff9f9f9f), thickness = 1.dp
//        )
//        Spacer(modifier = Modifier.width(7.dp))

        val focusManager = LocalFocusManager.current

        val newActions = KeyboardActions(
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
            modifier = Modifier
                .fillMaxHeight()
                .weight(1f)
                .padding(horizontal = 8.dp, vertical = 4.dp),
            contentAlignment = if (singleLine) Alignment.CenterStart else Alignment.TopStart,
        ) {
            BasicTextField(
                modifier = Modifier
                    .fillMaxWidth(),
                enabled = enabled,
                singleLine = singleLine,
                value = value,
                textStyle = TextStyle.Default.copy(
                    fontSize = 14.sp,
                    color = TextFieldColor.Text
                ),
                onValueChange = onValueChange,
                keyboardOptions = keyboardOptions,
                keyboardActions = newActions,
                cursorBrush = SolidColor(TextFieldColor.Text)
            )
            if (value.isEmpty()) {
                placeholder?.let { it() }
            }
        }


        trailingIcon?.let { it() }

//        Spacer(modifier = Modifier.width(10.dp))

    }
}
