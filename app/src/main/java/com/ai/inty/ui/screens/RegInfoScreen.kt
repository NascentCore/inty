package com.ai.inty.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.ai.inty.R
import com.ai.inty.base.ToastUtils
import com.ai.inty.beans.GENDER
import com.ai.inty.ui.components.AgeItem
import com.ai.inty.ui.components.CloseButton
import com.ai.inty.ui.components.EnterButton
import com.ai.inty.ui.components.GenderItem
import com.ai.inty.ui.components.LabelText
import com.ai.inty.ui.components.SubtitleText
import com.ai.inty.ui.components.TitleText
import kotlinx.coroutines.launch

/**
 * 注册信息屏幕
 */
@Composable
internal fun RegInfoScreen(
    onClose: () -> Unit = {},
    onSave: (gender: GENDER, age: String) -> Unit = { gender, age -> },
) {
    var selectGender by remember { mutableStateOf(GENDER.OTHER) }
    var selectAge by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(0.6f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color(0xFF322341),
                            Color(0xFF120E24)
                        )
                    ),
                    shape = RoundedCornerShape(24.dp, 24.dp, 0.dp, 0.dp)
                )
        ) {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                CloseButton(onClose = onClose)
            }
            Spacer(Modifier.height(6.dp))

            TitleText(title = stringResource(R.string.hello_wave))
            Spacer(Modifier.height(13.dp))
            TitleText(title = stringResource(R.string.welcome_to_intellimate))
            Spacer(Modifier.height(8.dp))
            SubtitleText(subtitle = stringResource(R.string.tell_us_more))
            Spacer(Modifier.height(26.dp))

            LabelText(label = stringResource(R.string.which_pronoun_use))
            Spacer(Modifier.height(12.dp))

            // 性别选择
            Row(
                modifier = Modifier.fillMaxWidth(),
            ) {
                Spacer(Modifier.width(40.dp))
                GenderItem(
                    gender = GENDER.MALE,
                    selected = (selectGender == GENDER.MALE),
                    onClick = {
                        selectGender = GENDER.MALE
                    }
                )
                Spacer(Modifier.weight(0.5f))
                GenderItem(
                    gender = GENDER.FEMALE,
                    selected = (selectGender == GENDER.FEMALE),
                    onClick = {
                        selectGender = GENDER.FEMALE
                    }
                )
                Spacer(Modifier.weight(0.5f))
                GenderItem(
                    gender = GENDER.OTHER,
                    selected = (selectGender == GENDER.OTHER),
                    onClick = {
                        selectGender = GENDER.OTHER
                    }
                )
                Spacer(Modifier.width(40.dp))
            }

            Spacer(Modifier.height(16.dp))
            LabelText(label = stringResource(R.string.what_is_your_age))
            Spacer(Modifier.height(12.dp))

            // 年龄选择
            FlowRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 24.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                maxItemsInEachRow = 2
            ) {
                val itemModifier = Modifier
                    .weight(1f)
                    .height(48.dp)

                AgeItem(
                    itemModifier,
                    text = stringResource(R.string.age_under_18),
                    isSelected = (selectAge == "<18"),
                    onSelected = {
                        selectAge = "<18"
                    }
                )
                AgeItem(
                    itemModifier,
                    text = stringResource(R.string.age_18_20),
                    isSelected = (selectAge == "18-20"),
                    onSelected = {
                        selectAge = "18-20"
                    }
                )
                AgeItem(
                    itemModifier,
                    text = stringResource(R.string.age_21_23),
                    isSelected = (selectAge == "21-23"),
                    onSelected = {
                        selectAge = "21-23"
                    }
                )
                AgeItem(
                    itemModifier,
                    text = stringResource(R.string.age_24_29),
                    isSelected = (selectAge == "24-29"),
                    onSelected = {
                        selectAge = "24-29"
                    }
                )
                AgeItem(
                    itemModifier,
                    text = stringResource(R.string.age_30_36),
                    isSelected = (selectAge == "30-36"),
                    onSelected = {
                        selectAge = "30-36"
                    }
                )
                AgeItem(
                    itemModifier,
                    text = stringResource(R.string.age_above_36),
                    isSelected = (selectAge == "Above 36"),
                    onSelected = {
                        selectAge = "Above 36"
                    }
                )
            }

            Spacer(Modifier.height(64.dp))

            val coroutineScope = rememberCoroutineScope()
            val msg = stringResource(R.string.toast_fill_form_real_age)

            EnterButton(
                onEnter = {
                    if (selectAge == "<18") {
                        coroutineScope.launch {
                            ToastUtils.showToast(msg)
                        }
                    } else {
                        onSave(selectGender, selectAge)
                    }
                }
            )

            Spacer(Modifier.height(60.dp))
        }
    }
}

@Preview(backgroundColor = 0xFFffffff, showBackground = true)
@Composable
private fun RegInfoScreenPreview() {
    RegInfoScreen()
}
