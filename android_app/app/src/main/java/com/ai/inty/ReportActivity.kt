package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.ui.screens.ReportScreen
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.ReportViewModel
import com.inty.utils.log.EasyLog
import com.therouter.router.Autowired
import com.therouter.router.Route
import kotlinx.coroutines.launch

/** 举报页面 */
@Route(path = Constant.ROUTE_REPORT)
class ReportActivity : BaseActivity() {

  private val viewModel: ReportViewModel by viewModels()

  @Autowired var targetID: String = ""

  @Autowired var targetType: String = "USER"

  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    viewModel.targetID = targetID
    viewModel.targetType = targetType

    lifecycleScope.launch {
      viewModel.finishActivity.collect {
        if (it) {
          finish()
        }
      }
    }

    setContent { IntyTheme { ReportContent(viewModel = viewModel, onBack = { finish() }) } }
  }
}

/** 举报内容组件 */
@Composable
private fun ReportContent(viewModel: ReportViewModel, onBack: () -> Unit) {
  val reasons = viewModel.reasons.collectAsState()
  val selectIDs = viewModel.selectIDS
  val description = viewModel.description.collectAsState()
  val localImages = viewModel.localImages
  val isSubmitting = viewModel.isSubmitting.collectAsState()

  val galleryLauncher =
      rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
        imageUri?.let { viewModel.onAddImage(imageUri) }
      }

  ReportScreen(
      reasons = reasons.value,
      selectIDs = selectIDs,
      onClickReason = { id, isSelect ->
        EasyLog.log("onClickReason id = $id, isSelect = $isSelect")
        if (isSelect) {
          viewModel.selectIDS.add(id)
        } else {
          viewModel.selectIDS.remove(id)
        }
      },
      description = description.value,
      onDescriptionChange = { viewModel.setDescription(it) },
      images = localImages.toList(),
      onClickAddImage = { galleryLauncher.launch("image/*") },
      onSave = { viewModel.submit() },
      isSubmitting = isSubmitting.value,
      onBack = onBack,
  )
}
