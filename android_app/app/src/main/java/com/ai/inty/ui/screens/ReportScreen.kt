package com.ai.inty.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.ReportItem
import com.ai.inty.ui.components.ReportDescriptionContainer
import com.ai.inty.ui.components.ReportImageEvidenceContainer
import com.ai.inty.ui.components.ReportItem
import com.ai.inty.ui.components.ReportReasonsContainer
import com.ai.inty.ui.components.SaveBtn

/** 举报屏幕 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportScreen(
    onBack: () -> Unit = {},
    reasons: List<ReportItem>,
    selectIDs: Set<Int>,
    onClickReason: (Int, Boolean) -> Unit,
    description: String,
    onDescriptionChange: (String) -> Unit,
    images: List<String>,
    onClickAddImage: () -> Unit,
    onSave: () -> Unit,
    isSubmitting: Boolean = false,
) {
  val focusManager = LocalFocusManager.current

  Box(
      modifier =
          Modifier.fillMaxSize().clickable(
              interactionSource = remember { MutableInteractionSource() },
              indication = null,
          ) {
            focusManager.clearFocus()
          },
  ) {
    Column(
        modifier =
            Modifier.matchParentSize()
                .padding(horizontal = 16.dp)
                .imePadding()
                .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
      // 布局占位用
      CenterAlignedTopAppBar(
          title = {},
          colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
      )
      Spacer(Modifier.height(16.dp))

      // 举报原因
      ReportReasonsContainer(title = stringResource(R.string.npc_asterisk_full)) {
        reasons.forEach { reason ->
          val isSelected = selectIDs.contains(reason.id)
          ReportItem(
              text = reason.description,
              selected = isSelected,
              onClick = { onClickReason(reason.id, !isSelected) },
          )
        }
      }

      Spacer(Modifier.height(24.dp))

      // 举报描述
      ReportDescriptionContainer(
          title = stringResource(R.string.report_description),
          description = description,
          onDescriptionChange = onDescriptionChange,
          placeholder = stringResource(R.string.please_fill_feedback_full),
      )

      Spacer(Modifier.height(24.dp))

      // 图片证据
      ReportImageEvidenceContainer(
          title = stringResource(R.string.image_evidence_full),
          images = images,
          onClickAddImage = onClickAddImage,
      )

      Spacer(Modifier.height(60.dp))

      SaveBtn(onSave = onSave, isSubmitting = isSubmitting)
      Spacer(Modifier.height(60.dp))
    }

    // 顶部导航栏
    CenterAlignedTopAppBar(
        colors =
            TopAppBarDefaults.centerAlignedTopAppBarColors()
                .copy(containerColor = Color(0XFF1C1523)),
        title = {
          Text(
              text = stringResource(R.string.report),
              color = Color.White,
              fontWeight = FontWeight.SemiBold,
              fontSize = 20.sp,
          )
        },
        navigationIcon = {
          Image(
              modifier = Modifier.padding(horizontal = 12.dp).noRippleClickable { onBack() },
              painter = painterResource(R.drawable.back),
              contentDescription = null,
          )
        },
    )
  }
}

@Preview(showBackground = true)
@Composable
fun ReportScreenPreview() {
  val mockReasons =
      listOf(
          ReportItem(id = 1, description = "不当内容"),
          ReportItem(id = 2, description = "垃圾信息"),
          ReportItem(id = 3, description = "骚扰行为"),
      )

  ReportScreen(
      onBack = {},
      reasons = mockReasons,
      selectIDs = setOf(1),
      onClickReason = { _, _ -> },
      description = "这是一条举报描述",
      onDescriptionChange = {},
      images = listOf(),
      onClickAddImage = {},
      onSave = {},
  )
}
