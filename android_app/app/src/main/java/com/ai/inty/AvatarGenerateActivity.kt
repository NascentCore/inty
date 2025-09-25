package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.viewModels
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.noRippleClickable
import com.ai.inty.ui.theme.DarkPurple
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.utils.AvatarManager
import com.ai.inty.viewmodels.AvatarGenerateViewModel
import com.inty.utils.log.EasyLog
import com.therouter.router.Route

/**
 * Ai 模型形象的 封面头像生成页面
 */
@Route(path = Constant.ROUTE_AVATAR_GENERATE)
class AvatarGenerateActivity : BaseActivity() {

    private val viewModel: AvatarGenerateViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            IntyTheme {
                AvatarGeneratePage(
                    modifier = Modifier.fillMaxSize(),
                    viewModel = viewModel,
                    onBack = { finish() }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AvatarGeneratePage(
    modifier: Modifier = Modifier,
    viewModel: AvatarGenerateViewModel,
    onBack: () -> Unit,
) {
    val prompt by viewModel.prompt.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val generatedImageUrl by viewModel.generatedImageUrl.collectAsState()
    val generatedImageUrls by viewModel.generatedImageUrls.collectAsState()
    val selectedImageIndex by viewModel.selectedImageIndex.collectAsState()
    val errorMessage by viewModel.errorMessage.collectAsState()

    val focusManager = LocalFocusManager.current

    // Handle error messages
    LaunchedEffect(errorMessage) {
        errorMessage?.let { error ->
            viewModel.showNetworkAwareError(error)
            viewModel.clearError()
        }
    }

    Scaffold(
        modifier = modifier.background(DarkPurple),
        containerColor = DarkPurple,
        topBar = {
            CenterAlignedTopAppBar(
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors()
                    .copy(containerColor = Color.Transparent),
                title = {
                    Text(
                        text = stringResource(R.string.generate_avatar),
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                },
                navigationIcon = {
                    Image(
                        modifier = Modifier
                            .padding(horizontal = 12.dp)
                            .noRippleClickable { onBack() },
                        painter = painterResource(R.drawable.close),
                        contentDescription = null,
                    )
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .imePadding()
                .padding(
                    top = padding.calculateTopPadding(),
                    start = padding.calculateLeftPadding(LayoutDirection.Ltr),
                    end = padding.calculateRightPadding(LayoutDirection.Ltr)
                )
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp)
                .pointerInput(Unit) {
                    detectTapGestures(onTap = {
                        focusManager.clearFocus()
                    })
                },
            horizontalAlignment = Alignment.CenterHorizontally
        ) {

            Spacer(modifier = Modifier.height(24.dp))

            // Image Preview Section
            if (generatedImageUrls.isEmpty()) {
                AvatarPreviewSection(
                    imageUrl = generatedImageUrl,
                    isLoading = isLoading
                )
            } else {
                AvatarGridSection(
                    imageUrls = generatedImageUrls,
                    selectedIndex = selectedImageIndex,
                    onImageSelected = viewModel::selectImage,
                    prompt = prompt,
                    isLoading = isLoading,
                    onRegenerate = { _ ->
                        viewModel.regenerateAvatar()
                    }
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

            // Prompt Input Field
            PromptInputField(
                value = prompt,
                onValueChange = viewModel::updatePrompt
            )

            Spacer(modifier = Modifier.height(32.dp))

            // Generate Button
            GenerateButton(
                isLoading = isLoading,
                enabled = prompt.isNotBlank(),
                onClick = {
                    viewModel.generateAvatar(onNavigateBack = onBack)
                }
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Use Generated Avatar Button
            if (generatedImageUrls.isNotEmpty() || generatedImageUrl != null) {
                UseAvatarButton(
                    onClick = {
                        val selectedUrl = viewModel.getSelectedAvatarUrl()
                        if (selectedUrl != null) {
                            AvatarManager.setGeneratedAvatarUrl(selectedUrl)
                        }
                        onBack()
                    }
                )
            }

            Spacer(modifier = Modifier.height(32.dp))

        }
    }
}

@Composable
private fun AvatarPreviewSection(
    imageUrl: String?,
    isLoading: Boolean,
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(320.dp)
            .background(
                color = Color(0x1A78599A),
                shape = RoundedCornerShape(16.dp)
            ),
        contentAlignment = Alignment.Center
    ) {
        when {
            isLoading -> {
                ThreeDotLoadingAnimation()
            }

            imageUrl != null -> {
                EasyLog.log("Displaying image with URL: $imageUrl")
                AsyncImage(
                    model = imageUrl,
                    contentDescription = stringResource(R.string.content_desc_generated_avatar),
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(4.dp),
                    contentScale = ContentScale.Crop,
                    onSuccess = {
                        EasyLog.log("Image loaded successfully: $imageUrl")
                    },
                    onError = {
                        EasyLog.log("Failed to load image: $imageUrl", EasyLog.ERROR)
                    }
                )
            }

            else -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Image(
                        painter = painterResource(R.drawable.img_gen_agent_preview),
                        contentDescription = null,
                        modifier = Modifier.size(48.dp)
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = stringResource(R.string.preview_generated_avatar),
                        fontSize = 14.sp,
                        color = Color.White.copy(0.7f),
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        // Dashed border for empty state (matching CreateRoleActivity style)
        if (imageUrl == null && !isLoading) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val strokeWidth = 1.dp.toPx()
                val cornerRadius = 16.dp.toPx()
                val dashLength = 10.dp.toPx()
                val gapLength = 5.dp.toPx()

                drawRoundRect(
                    color = Color.Gray,
                    topLeft = androidx.compose.ui.geometry.Offset(strokeWidth / 2, strokeWidth / 2),
                    size = androidx.compose.ui.geometry.Size(
                        size.width - strokeWidth,
                        size.height - strokeWidth
                    ),
                    cornerRadius = CornerRadius(cornerRadius),
                    style = Stroke(
                        width = strokeWidth,
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(dashLength, gapLength))
                    )
                )
            }
        }
    }
}

@Composable
private fun PromptInputField(
    value: String,
    onValueChange: (String) -> Unit,
) {
    Column {
        Text(
            text = stringResource(R.string.describe_desired_avatar),
            fontSize = 16.sp,
            color = Color.White,
            fontWeight = FontWeight.Medium
        )
        Spacer(modifier = Modifier.height(12.dp))

        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    color = Color(0x1A78599A),
                    shape = RoundedCornerShape(12.dp)
                )
                .border(
                    width = 1.dp,
                    color = Color.White.copy(0.2f),
                    shape = RoundedCornerShape(12.dp)
                )
                .padding(16.dp)
                .height(120.dp),
            textStyle = TextStyle(
                color = Color.White,
                fontSize = 16.sp
            ),
            cursorBrush = SolidColor(Color.White),
            decorationBox = { innerTextField ->
                Box {
                    if (value.isEmpty()) {
                        Text(
                            text = stringResource(R.string.avatar_creation_hint_full),
                            fontSize = 16.sp,
                            color = Color.White.copy(0.5f)
                        )
                    }
                    innerTextField()
                }
            }
        )
    }
}

@Composable
private fun GenerateButton(
    isLoading: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled && !isLoading,
        colors = ButtonDefaults.buttonColors(
            containerColor = Color.Transparent,
            disabledContainerColor = Color.Transparent
        ),
        shape = RoundedCornerShape(25.dp),
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .background(
                brush = androidx.compose.ui.graphics.Brush.horizontalGradient(
                    colors = if (enabled && !isLoading) {
                        listOf(
                            Color(0xFFE91E63),
                            Color(0xFFFF9800)
                        )
                    } else {
                        listOf(
                            Color(0x4DE91E63),
                            Color(0x4DFF9800)
                        )
                    }
                ),
                shape = RoundedCornerShape(25.dp)
            )
    ) {
        if (isLoading) {
            CircularProgressIndicator(
                color = Color.White,
                modifier = Modifier.size(24.dp)
            )
        } else {
            Text(
                text = stringResource(R.string.generate_avatar_button),
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White
            )
        }
    }
}

@Composable
private fun UseAvatarButton(
    onClick: () -> Unit,
) {
    Button(
        onClick = onClick,
        colors = ButtonDefaults.buttonColors(
            containerColor = Color(0xFF2196F3)
        ),
        shape = RoundedCornerShape(25.dp),
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
    ) {
        Text(
            text = stringResource(R.string.use_this_avatar_button),
            fontSize = 16.sp,
            fontWeight = FontWeight.Medium,
            color = Color.White
        )
    }
}

@Composable
fun ThreeDotLoadingAnimation() {
    val infiniteTransition = rememberInfiniteTransition(label = "dots_loading")

    Row(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        repeat(3) { index ->
            val delay = index * 200
            val alpha by infiniteTransition.animateFloat(
                initialValue = 0.3f,
                targetValue = 1.0f,
                animationSpec = infiniteRepeatable(
                    animation = tween(600, delayMillis = delay)
                ), label = "dot_alpha_$index"
            )

            Box(
                modifier = Modifier
                    .size(12.dp)
                    .background(
                        color = Color(0xFFE91E63).copy(alpha = alpha),
                        shape = CircleShape
                    )
            )
        }
    }
}

@Composable
private fun AvatarGridSection(
    imageUrls: List<String>,
    selectedIndex: Int,
    onImageSelected: (Int) -> Unit,
    prompt: String,
    isLoading: Boolean,
    onRegenerate: (String) -> Unit,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Regen 按钮
        RegenButton(
            onClick = {
                onRegenerate(prompt)
            },
            enabled = !isLoading
        )

        Spacer(modifier = Modifier.height(16.dp))

        // 4张图片的网格布局
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            imageUrls.take(4).forEachIndexed { index, imageUrl ->
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .aspectRatio(9 / 16f)
                        .background(
                            color = Color(0x1A78599A),
                            shape = RoundedCornerShape(8.dp)
                        )
                        .border(
                            width = if (index == selectedIndex) 3.dp else 1.dp,
                            color = if (index == selectedIndex) Color(0xFFE91E63) else Color.Transparent,
                            shape = RoundedCornerShape(8.dp)
                        )
                        .noRippleClickable { onImageSelected(index) },
                    contentAlignment = Alignment.Center
                ) {
                    AsyncImage(
                        model = imageUrl,
                        contentDescription = stringResource(
                            R.string.content_desc_generated_avatar_index,
                            index
                        ),
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(4.dp),
                        contentScale = ContentScale.Crop
                    )
                }
            }
        }
    }
}

@Composable
fun RegenButton(
    onClick: () -> Unit,
    enabled: Boolean = true,
) {
    Box(
        modifier = Modifier
            .fillMaxSize()
            .heightIn(112.dp)
            .background(
                color = Color(0x1A78599A),
                shape = RoundedCornerShape(8.dp)
            )
            .border(
                width = 1.dp,
                color = if (enabled) Color.Gray else Color.White.copy(0.2f),
                shape = RoundedCornerShape(8.dp)
            )
            .noRippleClickable { if (enabled) onClick() },
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = stringResource(R.string.regen_button),
            fontSize = 14.sp,
            fontWeight = FontWeight.Medium,
            color = if (enabled) Color.White else Color.White.copy(0.5f)
        )
    }
}
