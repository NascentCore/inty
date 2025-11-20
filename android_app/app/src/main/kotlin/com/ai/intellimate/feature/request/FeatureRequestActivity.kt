package com.ai.intellimate.feature.request

import ai.sxwl.android.common.base.BaseActivity
import android.content.Context
import android.content.Intent
import androidx.activity.viewModels
import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.lifecycleScope
import com.ai.intellimate.R
import com.ai.intellimate.ViewModelEvent
import com.ai.intellimate.agent.report.FeedbackFormContent
import kotlinx.coroutines.launch

/**
 * Feature Request 页面
 */
class FeatureRequestActivity : BaseActivity() {

    companion object {
        fun launch(context: Context) {
            context.startActivity(Intent(context, FeatureRequestActivity::class.java))
        }
    }

    private val viewModel: FeatureRequestViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        lifecycleScope.launch {
            viewModel.events.collect { event ->
                if (event is ViewModelEvent.ReportSubmitted) {
                    finish()
                }
            }
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        val title = stringResource(R.string.str_feature_request)
        val reasonsTitle = stringResource(R.string.feature_request_reasons_label)
        val descriptionTitle = stringResource(R.string.feature_request_description_label)
        val descriptionPlaceholder = stringResource(R.string.feature_request_description_placeholder)
        val imageEvidenceTitle = stringResource(R.string.feature_request_image_label)
        val submitButtonText = stringResource(R.string.feature_request_submit_button)

        FeedbackFormContent(
            viewModel = viewModel,
            onBack = { finish() },
            titleText = title,
            reasonsTitle = reasonsTitle,
            descriptionTitle = descriptionTitle,
            descriptionPlaceholder = descriptionPlaceholder,
            imageEvidenceTitle = imageEvidenceTitle,
            submitButtonText = submitButtonText,
        )
    }
}
