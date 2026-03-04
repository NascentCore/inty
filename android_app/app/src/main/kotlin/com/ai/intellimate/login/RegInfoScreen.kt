package com.ai.intellimate.login

import ai.sxwl.android.data.api.model.GENDER
import ai.sxwl.android.utils.ToastUtils
import androidx.activity.compose.BackHandler
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
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.stringArrayResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.AgeItem
import com.ai.intellimate.ui.components.EnterButton
import com.ai.intellimate.ui.components.GenderItem
import com.ai.intellimate.ui.components.LabelText
import com.ai.intellimate.ui.components.MbtiTypeChip
import com.ai.intellimate.ui.components.SubtitleText
import com.ai.intellimate.ui.components.TitleText
import kotlinx.coroutines.launch

private const val REG_INFO_MBTI_ITEMS_PER_ROW = 4

/** 注册信息屏幕 */
@Composable
internal fun RegInfoScreen(
    onClose: () -> Unit = {},
    onSave: (gender: GENDER, age: String, mbti: String) -> Unit = { _, _, _ -> },
) {
    var selectGender by remember { mutableStateOf<GENDER?>(null) }
    var selectAge by remember { mutableStateOf("") }
    var selectMbti by remember { mutableStateOf("") }

    val coroutineScope = rememberCoroutineScope()
    val requireGenderMsg = stringResource(R.string.toast_reginfo_required_select_gender)
    val requireAgeMsg = stringResource(R.string.toast_age_screen_required_select_age)
    val requireMbtiMsg = stringResource(R.string.toast_reginfo_required_select_mbti)
    val notEligibleMsg = stringResource(R.string.toast_age_screen_not_eligible)
    val mbtiTypeOptions = stringArrayResource(R.array.mbti_personality_types).toList()
    val mbtiRows = remember(mbtiTypeOptions) { mbtiTypeOptions.chunked(REG_INFO_MBTI_ITEMS_PER_ROW) }
    val mbtiSectionHorizontalPadding = dimensionResource(R.dimen.reg_info_mbti_section_horizontal_padding)
    val mbtiChipSpacing = dimensionResource(R.dimen.reg_info_mbti_chip_spacing)
    val mbtiSectionTopSpacing = dimensionResource(R.dimen.reg_info_mbti_section_top_spacing)
    val mbtiSectionBottomSpacing = dimensionResource(R.dimen.reg_info_mbti_section_bottom_spacing)

    // 统一提交逻辑，保持系统返回键与 Enter 按钮行为一致
    val submitRegInfo: () -> Unit = {
        when {
            selectGender == null -> {
                coroutineScope.launch { ToastUtils.showShort(requireGenderMsg) }
            }
            selectAge.isEmpty() || selectAge.isBlank() -> {
                coroutineScope.launch { ToastUtils.showShort(requireAgeMsg) }
            }
            selectAge == "<18" -> {
                coroutineScope.launch { ToastUtils.showShort(notEligibleMsg) }
            }
            selectMbti.isBlank() -> {
                coroutineScope.launch { ToastUtils.showShort(requireMbtiMsg) }
            }
            else -> {
                // 保存数据，成功后会自动关闭并申请通知权限
                onSave(selectGender!!, selectAge, selectMbti)
            }
        }
    }

    // 拦截系统返回键
    BackHandler(enabled = true) { submitRegInfo() }

    Box(modifier = Modifier.fillMaxSize().background(Color.Black.copy(0.6f))) {
        Column(
            modifier =
                Modifier.fillMaxWidth()
                    .align(Alignment.BottomCenter)
                    .background(
                        brush =
                            Brush.verticalGradient(
                                colors = listOf(Color(0xFF322341), Color(0xFF120E24))
                            ),
                        shape = RoundedCornerShape(24.dp, 24.dp, 0.dp, 0.dp),
                    )
        ) {
            Spacer(Modifier.height(26.dp))

            TitleText(title = stringResource(R.string.hello_wave))
            Spacer(Modifier.height(13.dp))
            TitleText(title = stringResource(R.string.welcome_to_intellimate))
            Spacer(Modifier.height(8.dp))
            SubtitleText(subtitle = stringResource(R.string.tell_us_more))
            Spacer(Modifier.height(26.dp))

            LabelText(label = stringResource(R.string.which_pronoun_use))
            Spacer(Modifier.height(12.dp))

            // 性别选择
            Row(modifier = Modifier.fillMaxWidth()) {
                Spacer(Modifier.width(40.dp))
                GenderItem(
                    gender = GENDER.MALE,
                    selected = (selectGender == GENDER.MALE),
                    onClick = { selectGender = GENDER.MALE },
                )
                Spacer(Modifier.weight(0.5f))
                GenderItem(
                    gender = GENDER.FEMALE,
                    selected = (selectGender == GENDER.FEMALE),
                    onClick = { selectGender = GENDER.FEMALE },
                )
                Spacer(Modifier.weight(0.5f))
                GenderItem(
                    gender = GENDER.OTHER,
                    selected = (selectGender == GENDER.OTHER),
                    onClick = { selectGender = GENDER.OTHER },
                )
                Spacer(Modifier.width(40.dp))
            }

            Spacer(Modifier.height(16.dp))
            LabelText(label = stringResource(R.string.what_is_your_age))
            Spacer(Modifier.height(12.dp))

            // 年龄选择
            FlowRow(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 24.dp),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                maxItemsInEachRow = 2,
            ) {
                val itemModifier = Modifier.weight(1f).height(48.dp)

                AgeItem(
                    itemModifier,
                    text = stringResource(R.string.age_under_18),
                    isSelected = (selectAge == "<18"),
                    onSelected = { selectAge = "<18" },
                )
                AgeItem(
                    itemModifier,
                    text = "18-25",
                    isSelected = (selectAge == "18-25"),
                    onSelected = { selectAge = "18-25" },
                )
                AgeItem(
                    itemModifier,
                    text = "26-35",
                    isSelected = (selectAge == "26-35"),
                    onSelected = { selectAge = "26-35" },
                )
                AgeItem(
                    itemModifier,
                    text = "36-45",
                    isSelected = (selectAge == "36-45"),
                    onSelected = { selectAge = "36-45" },
                )
                AgeItem(
                    itemModifier,
                    text = "46-55",
                    isSelected = (selectAge == "46-55"),
                    onSelected = { selectAge = "46-55" },
                )
                AgeItem(
                    itemModifier,
                    text = "55+",
                    isSelected = (selectAge == "Above 55"),
                    onSelected = { selectAge = "Above 55" },
                )
            }

            Spacer(Modifier.height(mbtiSectionTopSpacing))
            LabelText(label = stringResource(R.string.what_is_your_mbti))
            Spacer(Modifier.height(8.dp))
            SubtitleText(subtitle = stringResource(R.string.mbti_selection_hint))
            Spacer(Modifier.height(12.dp))

            Column(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(horizontal = mbtiSectionHorizontalPadding),
                verticalArrangement = Arrangement.spacedBy(mbtiChipSpacing),
            ) {
                mbtiRows.forEach { rowItems ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(mbtiChipSpacing),
                    ) {
                        rowItems.forEach { mbtiType ->
                            MbtiTypeChip(
                                modifier = Modifier.weight(1f),
                                mbtiType = mbtiType,
                                selected = (selectMbti == mbtiType),
                                onClick = { selectMbti = mbtiType },
                            )
                        }
                        repeat(REG_INFO_MBTI_ITEMS_PER_ROW - rowItems.size) {
                            Spacer(modifier = Modifier.weight(1f))
                        }
                    }
                }
            }

            Spacer(Modifier.height(mbtiSectionBottomSpacing))

            EnterButton(
                onEnter = {
                    submitRegInfo()
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
