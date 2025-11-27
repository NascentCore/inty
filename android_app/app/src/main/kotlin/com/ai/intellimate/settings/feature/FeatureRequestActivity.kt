// CREATED_BY_AGENT
package com.ai.intellimate.settings.feature

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.design.noRippleClickable
import android.content.Context
import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.ui.components.ReportDescriptionContainer
import com.ai.intellimate.ui.components.ReportItem
import com.ai.intellimate.ui.components.ReportReasonsContainer
import com.ai.intellimate.ui.components.SaveBtn
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

class FeatureRequestActivity : BaseActivity() {

    private val viewModel: FeatureRequestViewModel by viewModels()

    companion object {
        fun launch(context: Context) {
            context.startActivity(Intent(context, FeatureRequestActivity::class.java))
        }
    }

    override fun initConfigData() {
        super.initConfigData()
        lifecycleScope.launch {
            viewModel.events.collectLatest { event ->
                when (event) {
                    FeatureRequestEvent.Submitted -> finish()
                }
            }
        }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        val selectedCategory by viewModel.selectedCategory.collectAsState()
        val description by viewModel.description.collectAsState()
        val imageUris by viewModel.imageUris.collectAsState()
        val isSubmitting by viewModel.isSubmitting.collectAsState()

        val galleryLauncher =
            rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
                uri?.let { viewModel.onAddImage(it) }
            }

        FeatureRequestScreen(
            categories = viewModel.categories,
            selectedCategory = selectedCategory,
            description = description,
            images = imageUris,
            isSubmitting = isSubmitting,
            onSelectCategory = { viewModel.selectCategory(it) },
            onDescriptionChange = { viewModel.updateDescription(it) },
            onPickImage = { galleryLauncher.launch("image/*") },
            onRemoveImage = { viewModel.clearImage() },
            onSubmit = { viewModel.submit() },
            onBack = { finish() },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FeatureRequestScreen(
    categories: List<FeatureRequestCategory>,
    selectedCategory: FeatureRequestCategoryType?,
    description: String,
    images: List<String>,
    isSubmitting: Boolean,
    onSelectCategory: (FeatureRequestCategoryType) -> Unit,
    onDescriptionChange: (String) -> Unit,
    onPickImage: () -> Unit,
    onRemoveImage: () -> Unit,
    onSubmit: () -> Unit,
    onBack: () -> Unit,
) {
    val focusManager = LocalFocusManager.current

    Box(
        modifier =
            Modifier.fillMaxSize().background(Color.Transparent).clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
            ) {
                focusManager.clearFocus()
            }
    ) {
        Column(
            modifier =
                Modifier.matchParentSize()
                    .padding(horizontal = 16.dp)
                    .imePadding()
                    .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            CenterAlignedTopAppBar(
                title = {},
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.Transparent),
            )
            Spacer(Modifier.height(16.dp))

            ReportReasonsContainer(title = stringResource(R.string.feature_request_category_title)) {
                categories.forEach { category ->
                    val label = stringResource(category.titleRes)
                    ReportItem(
                        text = label,
                        selected = category.type == selectedCategory,
                        onClick = { onSelectCategory(category.type) },
                    )
                }
            }

            Spacer(Modifier.height(24.dp))

            ReportDescriptionContainer(
                title = stringResource(R.string.feature_request_description_title),
                description = description,
                onDescriptionChange = onDescriptionChange,
                placeholder = stringResource(R.string.feature_request_description_placeholder),
            )

            Spacer(Modifier.height(24.dp))

            FeatureRequestImageSection(
                imageUrl = images.firstOrNull(),
                onPickImage = onPickImage,
                onRemoveImage = onRemoveImage,
            )

            Spacer(Modifier.height(60.dp))

            SaveBtn(onSave = onSubmit, isSubmitting = isSubmitting)

            Spacer(Modifier.height(60.dp))
        }

        CenterAlignedTopAppBar(
            colors =
                TopAppBarDefaults.centerAlignedTopAppBarColors()
                    .copy(containerColor = Color(0xFF1C1523)),
            title = {
                Text(
                    text = stringResource(R.string.feature_request_title),
                    color = Color.White,
                    fontWeight = FontWeight.SemiBold,
                    fontSize = 20.sp,
                )
            },
            navigationIcon = {
                Image(
                    modifier =
                        Modifier.padding(horizontal = 12.dp).noRippleClickable { onBack() },
                    painter = painterResource(R.drawable.back),
                    contentDescription = null,
                )
            },
        )
    }
}

@Composable
private fun FeatureRequestImageSection(
    imageUrl: String?,
    onPickImage: () -> Unit,
    onRemoveImage: () -> Unit,
) {
    val context = LocalContext.current
    Column(
        modifier =
            Modifier.fillMaxWidth()
                .background(
                    color = Color(0x1A78599A),
                    shape = RoundedCornerShape(8.dp),
                )
                .border(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(
                                    Color.Transparent,
                                    Color.White.copy(alpha = 0.2f),
                                    Color.Transparent,
                                )
                        ),
                    width = 1.dp,
                    shape = RoundedCornerShape(8.dp),
                )
                .padding(horizontal = 12.dp),
    ) {
        Spacer(Modifier.height(16.dp))
        Text(
            modifier = Modifier.fillMaxWidth(),
            text = stringResource(R.string.feature_request_image_title),
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
        Spacer(Modifier.height(12.dp))

        Box(
            modifier =
                Modifier.size(88.dp)
                    .align(Alignment.Start)
                    .clip(RoundedCornerShape(8.dp))
                    .background(color = Color.White.copy(alpha = 0.1f), shape = RoundedCornerShape(8.dp))
                    .noRippleClickable { onPickImage() },
        ) {
            if (imageUrl != null) {
                AsyncImage(
                    modifier = Modifier.matchParentSize(),
                    model = ImageRequest.Builder(context).data(imageUrl).build(),
                    contentDescription = null,
                )
            } else {
                Image(
                    modifier = Modifier.size(26.dp).align(Alignment.Center),
                    painter = painterResource(R.drawable.btn_add6),
                    contentDescription = null,
                )
            }
        }

        Text(
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
            text = stringResource(R.string.feature_request_image_hint),
            fontSize = 12.sp,
            color = Color.White.copy(alpha = 0.6f),
        )

        if (imageUrl != null) {
            Text(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(top = 8.dp, bottom = 12.dp)
                        .noRippleClickable { onRemoveImage() },
                text = stringResource(R.string.feature_request_remove_image),
                fontSize = 12.sp,
                color = Color(0xFFFF905D),
            )
        } else {
            Spacer(Modifier.height(12.dp))
        }

        Spacer(Modifier.height(16.dp))
    }
}
