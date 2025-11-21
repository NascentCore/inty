package com.ai.intellimate.agent.generate

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.design.AntiClick
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
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
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.graphics.toColorInt
import androidx.core.net.toUri
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.viewModelScope
import coil3.compose.AsyncImage
import com.ai.intellimate.R
import com.ai.intellimate.ui.SingleLineTextInputField
import com.ai.intellimate.utils.AvatarManager
import com.ai.intellimate.xb.components.MultiLineBasicTextField
import com.architecture.httplib.core.HttpResult
import com.yalantis.ucrop.UCrop
import com.yalantis.ucrop.UCropActivity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.net.URL
import java.util.UUID
import java.util.concurrent.TimeUnit
import android.graphics.Color as AndroidColor

/** 创建角色的页面 */
class CreateRoleActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_AGENT_INFO = "intent_key_agent_info"

        /**
         * 启动创建/编辑角色界面
         *
         * @param context 上下文context
         * @param agentInfo Agent的Info对象，为null时表示创建新角色，否则表示编辑现有角色
         */
        fun launch(context: Context, agentInfo: AgentInfo? = null) {
            context.startActivity(
                Intent(context, CreateRoleActivity::class.java).also { intent ->
                    intent.putExtra(INTENT_KEY_AGENT_INFO, agentInfo)
                }
            )
        }

        /**
         * 获取创建/编辑角色界面的 Intent（用于 Activity Result）
         *
         * @param context 上下文context
         * @param agentInfo Agent的Info对象，为null时表示创建新角色，否则表示编辑现有角色
         * @return 配置好的 Intent
         */
        fun getIntent(context: Context, agentInfo: AgentInfo? = null): Intent {
            return Intent(context, CreateRoleActivity::class.java).apply {
                putExtra(INTENT_KEY_AGENT_INFO, agentInfo)
            }
        }
    }

    private var agent: AgentInfo? = null
    private val createRoleViewModel: CreateRoleViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        agent =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(INTENT_KEY_AGENT_INFO, AgentInfo::class.java)
            } else {
                @Suppress("DEPRECATION") intent.getParcelableExtra(INTENT_KEY_AGENT_INFO)
            }
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        CreateRolePage(
            modifier = Modifier.fillMaxSize(),
            createRoleViewModel = createRoleViewModel,
            onBack = { finish() },
            onCreateSuccess = {
                setResult(Activity.RESULT_OK)
                finish()
            },
            onAvatarGenerateClick = { AvatarGenerateActivity.Companion.launch(this) },
            editAgent = agent,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CreateRolePage(
    modifier: Modifier = Modifier,
    createRoleViewModel: CreateRoleViewModel,
    onBack: () -> Unit,
    onCreateSuccess: () -> Unit,
    onAvatarGenerateClick: () -> Unit,
    editAgent: AgentInfo? = null,
) {
    val isEditMode = editAgent != null

    var name by remember { mutableStateOf(editAgent?.name ?: "") }
    var gender by remember { mutableStateOf(editAgent?.gender ?: "FEMALE") }
    var settings by remember {
        mutableStateOf(
            editAgent?.settings?.get("description") as? String ?: editAgent?.prompt ?: ""
        )
    }
    var intro by remember { mutableStateOf(editAgent?.intro ?: "") }
    var opening by remember { mutableStateOf(editAgent?.opening ?: "") }
    var visibility by remember { mutableStateOf(editAgent?.visibility ?: "PRIVATE") }
    var isLoading by remember { mutableStateOf(false) }
    // Initialize image states based on edit mode
    var avatarUrl by remember {
        mutableStateOf<String?>(
            if (isEditMode && editAgent.backgroundImages.isEmpty()) {
                // If no background images array, use single background field
                editAgent.background.takeIf { it.isNotBlank() }
            } else null
        )
    }
    var avatarUrls by remember {
        mutableStateOf<List<String>>(if (isEditMode) editAgent.backgroundImages else emptyList())
    }
    var selectedImageIndex by remember {
        mutableIntStateOf(
            if (isEditMode && editAgent.backgroundImages.isNotEmpty()) {
                // Find the index of the background image in the background_images list
                val backgroundUrl = editAgent.background.takeIf { it.isNotBlank() }
                if (backgroundUrl != null) {
                    val index = editAgent.backgroundImages.indexOf(backgroundUrl)
                    if (index >= 0) index else 0
                } else {
                    0
                }
            } else {
                0
            }
        )
    }
    var isGeneratingAvatar by remember { mutableStateOf(false) }
    var croppedAvatarUrl by remember {
        mutableStateOf<String?>(
            if (isEditMode)
                editAgent.avatar.takeIf { it.isNotBlank() && it != editAgent.background }
            else null
        )
    }

    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val focusManager = LocalFocusManager.current

    // Clear avatar data when creating new character
    LaunchedEffect(isEditMode) {
        if (!isEditMode) {
            AvatarManager.clearAllAvatarData()
            LogUtils.i("Cleared avatar data for new character creation")
        }
    }

    // Clean up AvatarManager when leaving the activity
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_STOP -> {
                    // Clear AvatarManager when activity is stopped (user navigates away)
                    LogUtils.i("Activity stopped - clearing AvatarManager data")
                    AvatarManager.clearAllAvatarData()
                }

                Lifecycle.Event.ON_DESTROY -> {
                    // Also clear when activity is destroyed
                    LogUtils.i("Activity destroyed - clearing AvatarManager data")
                    AvatarManager.clearAllAvatarData()
                }

                else -> {}
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    // UCrop launcher for avatar cropping
    val cropLauncher =
        rememberLauncherForActivityResult(
            contract = ActivityResultContracts.StartActivityForResult()
        ) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                result.data?.let { data ->
                    val resultUri = UCrop.getOutput(data)
                    if (resultUri != null) {
                        LogUtils.i("Avatar cropped successfully: $resultUri")

                        // Upload the cropped image to server
                        try {
                            val file = File(resultUri.path!!)
                            val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
                            val body =
                                MultipartBody.Part.createFormData("file", file.name, requestFile)

                            val agentApi = NetServiceMgr.getAgentApi()
                            // Use CreateRoleViewModel's scope to launch the coroutine
                            createRoleViewModel.viewModelScope.launch(Dispatchers.IO) {
                                try {
                                    val response = agentApi.uploadAvatar(body)
                                    when (response) {
                                        is HttpResult.Success -> {
                                            val uploadedUrl = response.data.url
                                            LogUtils.i("Avatar uploaded successfully: $uploadedUrl")

                                            // Update UI on main thread
                                            withContext(Dispatchers.Main) {
                                                croppedAvatarUrl = uploadedUrl
                                                ToastUtils.showShort(
                                                    R.string.toast_avatar_cropped_uploaded
                                                )
                                            }
                                        }

                                        is HttpResult.Failure -> {
                                            LogUtils.e("Upload failed: ${response.message}")
                                            withContext(Dispatchers.Main) {
                                                ToastUtils.showShort(
                                                    context.getString(
                                                        R.string.toast_upload_failed_with_message,
                                                        response.message ?: "Unknown error",
                                                    )
                                                )
                                            }
                                        }
                                    }
                                } catch (e: Exception) {
                                    LogUtils.e("Upload exception: ${e.message}")
                                    withContext(Dispatchers.Main) {
                                        ToastUtils.showShort(
                                            context.getString(
                                                R.string.toast_upload_failed_with_message,
                                                e.message ?: "Unknown error",
                                            )
                                        )
                                    }
                                }
                            }
                        } catch (e: Exception) {
                            LogUtils.e("Failed to prepare upload: ${e.message}")
                            ToastUtils.showShort(
                                context.getString(
                                    R.string.toast_failed_prepare_upload_with_message,
                                    e.message ?: "Unknown error",
                                )
                            )
                        }
                    }
                }
            } else if (result.resultCode == UCrop.RESULT_ERROR) {
                result.data?.let { data ->
                    val cropError = UCrop.getError(data)
                    LogUtils.e("UCrop error: ${cropError?.message}")
                    ToastUtils.showShort(
                        context.getString(R.string.toast_crop_failed, cropError?.message ?: "")
                    )
                }
            }
        }

    // 检查是否有生成的头像URL - 使用DisposableEffect来监听生命周期
    DisposableEffect(Unit) {
        val checkAvatarStatus = {

            // Check if generation is in progress
            val generatingStatus = AvatarManager.isGenerating()
            isGeneratingAvatar = generatingStatus

            // Check for multiple generated URLs
            val currentUrls = AvatarManager.getCurrentAvatarUrls()
            if (currentUrls.isNotEmpty()) {
                avatarUrls = currentUrls
                selectedImageIndex = AvatarManager.getSelectedImageIndex()
                avatarUrl = null // Clear single URL when we have multiple
            } else {
                // Check for single generated URL
                val generatedUrl = AvatarManager.getCurrentAvatarUrl()
                if (generatedUrl != null && generatedUrl.isNotBlank()) {
                    avatarUrl = generatedUrl
                    avatarUrls = emptyList()
                }
            }

            // Check for generation errors
            val error = AvatarManager.getGenerationError()
            if (error != null) {
                ToastUtils.showShort(error)
                isGeneratingAvatar = false
            }

            // Show current generation prompt if generating
            if (generatingStatus) {
                val prompt = AvatarManager.getGenerationPrompt()
                LogUtils.i("Currently generating with prompt: '$prompt'")
            }
        }

        // 初始检查
        checkAvatarStatus()

        onDispose {}
    }

    // 监听Activity生命周期，特别是onResume事件
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {

                // Check generation status
                isGeneratingAvatar = AvatarManager.isGenerating()

                // Check for multiple URLs
                val currentUrls = AvatarManager.getCurrentAvatarUrls()
                if (currentUrls.isNotEmpty() && currentUrls != avatarUrls) {
                    avatarUrls = currentUrls
                    selectedImageIndex = AvatarManager.getSelectedImageIndex()
                    avatarUrl = null
                } else {
                    // Check for single URL
                    val currentUrl = AvatarManager.getCurrentAvatarUrl()
                    if (currentUrl != null && currentUrl != avatarUrl) {
                        avatarUrl = currentUrl
                        avatarUrls = emptyList()
                    }
                }

                // Check for errors
                val error = AvatarManager.getGenerationError()
                if (error != null) {
                    ToastUtils.showShort(error)
                    isGeneratingAvatar = false
                }
            }
        }

        lifecycleOwner.lifecycle.addObserver(observer)

        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    // 添加LaunchedEffect来监听avatar生成状态
    LaunchedEffect(Unit) {
        // 定期检查生成状态 (作为备用机制)
        while (true) {
            delay(2000) // 每2秒检查一次

            val currentGenerationStatus = AvatarManager.isGenerating()
            if (currentGenerationStatus != isGeneratingAvatar) {
                isGeneratingAvatar = currentGenerationStatus
            }

            // 头像状态管理：多选模式优先，单选模式备选
            val currentUrls = AvatarManager.getCurrentAvatarUrls()
            if (currentUrls.isNotEmpty() && currentUrls != avatarUrls) {
                // 多选模式：AI生成了多个头像变体
                avatarUrls = currentUrls
                selectedImageIndex = AvatarManager.getSelectedImageIndex()
                avatarUrl = null
            } else {
                // 单选模式：单个头像（编辑模式/用户上传/AI生成单个头像）
                val currentUrl = AvatarManager.getCurrentAvatarUrl()
                if (currentUrl != null && currentUrl != avatarUrl) {
                    avatarUrl = currentUrl
                    avatarUrls = emptyList()
                }
            }

            val error = AvatarManager.getGenerationError()
            if (error != null) {
                ToastUtils.showShort(error)
                isGeneratingAvatar = false
            }
        }
    }

    Scaffold(
        modifier = modifier.background(HeartColor.primaryColor),
        containerColor = HeartColor.primaryColor,
        topBar = {
            CenterAlignedTopAppBar(
                colors =
                    TopAppBarDefaults.centerAlignedTopAppBarColors()
                        .copy(containerColor = Color.Transparent),
                title = {
                    Text(
                        text = if (isEditMode) "Edit IntelliMate" else "Create IntelliMate",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White,
                    )
                },
                navigationIcon = {
                    Image(
                        modifier =
                            Modifier
                                .padding(horizontal = 12.dp)
                                .noRippleClickable { onBack() },
                        painter = painterResource(R.drawable.close),
                        contentDescription = null,
                    )
                },
            )
        },
    ) { padding ->
        Column(
            modifier =
                Modifier
                    .fillMaxSize()
                    .imePadding()
                    .padding(
                        top = padding.calculateTopPadding(),
                        start = padding.calculateLeftPadding(LayoutDirection.Ltr),
                        end = padding.calculateRightPadding(LayoutDirection.Ltr),
                    )
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp)
                    .pointerInput(Unit) {
                        detectTapGestures(onTap = { focusManager.clearFocus() })
                    },
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Spacer(modifier = Modifier.height(24.dp))

            // Avatar Upload Section
            AvatarUploadSection(
                avatarUrl = avatarUrl,
                avatarUrls = avatarUrls,
                selectedIndex = selectedImageIndex,
                isGenerating = isGeneratingAvatar,
                croppedAvatarUrl = croppedAvatarUrl,
                onGenerateClick = {
                    onAvatarGenerateClick()
                    // 当点击生成头像时，不清除当前URL，让用户返回时检查新的URL
                },
                onImageSelected = { index ->
                    selectedImageIndex = index
                    AvatarManager.setSelectedImageIndex(index)
                },
                onRegenerate = { prompt ->
                    // Navigate to avatar generation page with existing prompt
                    onAvatarGenerateClick()
                },
                onFaceEdit = {
                    // Get the current avatar URL to crop
                    val imageUrl =
                        if (avatarUrls.isNotEmpty()) {
                            // Defensive bounds checking
                            val safeIndex =
                                if (
                                    selectedImageIndex >= 0 && selectedImageIndex < avatarUrls.size
                                ) {
                                    selectedImageIndex
                                } else {
                                    LogUtils.e(
                                        "Face edit - Index out of bounds! selectedImageIndex: $selectedImageIndex, avatarUrls.size: ${avatarUrls.size}"
                                    )
                                    0 // Fall back to first image
                                }

                            val selectedUrl = avatarUrls.getOrNull(safeIndex)
                            selectedUrl ?: avatarUrls.first()
                        } else {
                            avatarUrl
                        }

                    if (imageUrl != null) {
                        // Check if it's a web URL or local file
                        if (imageUrl.startsWith("http")) {
                            // Validate URL format
                            val isValidUrl =
                                try {
                                    URL(imageUrl) // Test if URL is valid
                                    true
                                } catch (e: Exception) {
                                    LogUtils.e(
                                        "Face edit - Invalid URL format: $imageUrl URL validation error: ${e.message}"
                                    )
                                    false
                                }

                            if (isValidUrl) {
                                // Download image from web URL first using OkHttp
                                createRoleViewModel.viewModelScope.launch(Dispatchers.IO) {
                                    try {
                                        // Download image to local cache using OkHttp
                                        val tempFile =
                                            File(
                                                context.cacheDir,
                                                "temp_crop_source_${UUID.randomUUID()}.jpg",
                                            )
                                        val client =
                                            OkHttpClient.Builder()
                                                .callTimeout(10 * 1000, TimeUnit.MILLISECONDS)
                                                .connectTimeout(15 * 1000, TimeUnit.MILLISECONDS)
                                                .readTimeout(15 * 1000, TimeUnit.MILLISECONDS)
                                                .writeTimeout(15 * 1000, TimeUnit.MILLISECONDS)
                                                .build()
                                        val request = Request.Builder().url(imageUrl).build()

                                        val response = client.newCall(request).execute()
                                        LogUtils.d(
                                            "Face edit download - HTTP response message: ${response.message}"
                                        )

                                        if (response.isSuccessful) {
                                            response.body?.let { body ->
                                                // ✅ 修复：将响应体内容写入临时文件
                                                tempFile.outputStream().use { output ->
                                                    body.byteStream().use { input ->
                                                        input.copyTo(output)
                                                    }
                                                }

                                                // 验证文件是否成功写入
                                                if (!tempFile.exists() || tempFile.length() == 0L) {
                                                    throw Exception("Failed to write image data to temp file")
                                                }

                                                LogUtils.d(
                                                    "Face edit download - Image downloaded successfully, file size: ${tempFile.length()} bytes"
                                                )

                                                withContext(Dispatchers.Main) {
                                                    startUCropWithLocalFile(
                                                        tempFile,
                                                        context,
                                                        cropLauncher,
                                                    )
                                                }
                                            } ?: run { throw Exception("Response body is null") }
                                        } else {
                                            throw Exception(
                                                "HTTP ${response.code}: ${response.message}"
                                            )
                                        }
                                    } catch (e: Exception) {
                                        LogUtils.e(
                                            "Failed to download image for cropping: $imageUrl Error details: ${e.message}"
                                        )
                                        withContext(Dispatchers.Main) {
                                            ToastUtils.showShort(
                                                R.string.toast_failed_download_image_editing
                                            )
                                        }
                                    }
                                }
                            } else {
                                ToastUtils.showShort(R.string.toast_invalid_image_url)
                            }
                        } else {
                            // Local file URI
                            val sourceFile =
                                if (imageUrl.startsWith("file://")) {
                                    File(imageUrl.toUri().path!!)
                                } else {
                                    File(imageUrl)
                                }
                            startUCropWithLocalFile(sourceFile, context, cropLauncher)
                        }
                    } else {
                        ToastUtils.showShort(R.string.toast_no_avatar_image)
                    }
                },
            )

            Spacer(modifier = Modifier.height(32.dp))

            // Name Field
            SingleLineTextInputField(
                label = "Name *",
                labelFontSize = 16.sp,
                inputValue = name,
                onValueChange = { name = it },
                inputFontSize = 16.sp,
                placeholder = "Name your IntelliMate",
            )

            // Gender Selection已经创建后的，也就是在修改模式下，性别选项则不显示
            if (!isEditMode) {
                Spacer(modifier = Modifier.height(24.dp))
                GenderSelectionSection(selectedGender = gender, onGenderChange = { gender = it })
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Settings Field
            CustomTextField(
                label = "Settings (Determines dialogue effect) *",
                value = settings,
                onValueChange = { settings = it },
                placeholder = "Please fill in the dialogue effect...",
                minLines = 4,
                maxLength = 800
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Intro Field
            CustomTextField(
                label = "Intro (No impact on dialogue effect) *",
                value = intro,
                onValueChange = { intro = it },
                placeholder = "Please fill in the character introduction...",
                minLines = 3,
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Opening Field
            CustomTextField(
                label = "Opening *",
                value = opening,
                onValueChange = { opening = it },
                placeholder = "Please fill in the character's opening remarks...",
                minLines = 3,
            )

            Spacer(modifier = Modifier.height(40.dp))

            // Create Button
            CreateButton(
                isLoading = isLoading,
                isEditMode = isEditMode,
                onClick = {
                    // Validate required fields
                    if (
                        name.isBlank() || intro.isBlank() || opening.isBlank() || settings.isBlank()
                    ) {
                        ToastUtils.showShort(R.string.please_fill_required_fields)
                        return@CreateButton
                    }

                    // Prepare avatar and background fields according to new logic
                    val backgroundUrl =
                        if (avatarUrls.isNotEmpty()) {
                            // Use selected image from generated grid as background
                            avatarUrls.getOrNull(selectedImageIndex) ?: avatarUrls.first()
                        } else {
                            // Use single generated image as background
                            avatarUrl
                        }

                    // 头像数据更新
                    if (isEditMode) {
                        // 更新ai 形象的背景选择
                        if (backgroundUrl != editAgent.background) {
                            // 此时如果头像数据还是旧的，则手动更新为最新背景的
                            if (croppedAvatarUrl == editAgent.avatar) {
                                croppedAvatarUrl = backgroundUrl
                            }
                        }
                    }
                    val finalAvatarUrl = croppedAvatarUrl ?: backgroundUrl
                    val backgroundImagesList = avatarUrls.ifEmpty { listOfNotNull(avatarUrl) }

                    // Save background for chat usage
                    if (backgroundUrl != null) {
                        AvatarManager.setChatBackgroundUrl(backgroundUrl)
                    }

                    isLoading = true

                    try {
                        val request =
                            CreateAgentRequest(
                                name = name,
                                gender = gender,
                                avatar = finalAvatarUrl,
                                background = backgroundUrl,
                                backgroundImages = backgroundImagesList,
                                settings = mapOf("description" to settings),
                                intro = intro,
                                opening = opening,
                                visibility = visibility,
                                prompt = settings,
                            )
                        // Call API through ViewModel
                        if (isEditMode) {
                            createRoleViewModel.updateAgent(
                                agentId = editAgent.id,
                                request = request,
                                onSuccess = { agentInfo ->
                                    isLoading = false
                                    ToastUtils.showShort(R.string.character_updated_successfully)
                                    onCreateSuccess()
                                },
                                onError = { error ->
                                    isLoading = false
                                    val errorMessage =
                                        if (error.isBlank()) {
                                            context.getString(
                                                R.string.operation_failed_try_later,
                                                context.getString(R.string.update_failed),
                                                context.getString(R.string.please_try_again_later),
                                            )
                                        } else {
                                            context.getString(
                                                R.string.update_failed_with_reason,
                                                error,
                                            )
                                        }
                                    ToastUtils.showShort(errorMessage)
                                },
                            )
                        } else {
                            createRoleViewModel.createAgent(
                                request = request,
                                onSuccess = { agentInfo ->
                                    isLoading = false
                                    ToastUtils.showShort(
                                        context.getString(R.string.create_ai_successfully)
                                    )
                                    onCreateSuccess()
                                },
                                onError = { error ->
                                    isLoading = false
                                    val errorMessage =
                                        if (error.isBlank()) {
                                            context.getString(
                                                R.string.operation_failed_try_later,
                                                context.getString(R.string.creation_failed),
                                                context.getString(R.string.please_try_again_later),
                                            )
                                        } else {
                                            context.getString(
                                                R.string.creation_failed_with_reason,
                                                error,
                                            )
                                        }
                                    ToastUtils.showShort(errorMessage)
                                },
                            )
                        }
                    } catch (e: Exception) {
                        isLoading = false
                        val operation =
                            if (isEditMode) context.getString(R.string.update_failed)
                            else context.getString(R.string.creation_failed)
                        val errorMessage =
                            context.getString(
                                R.string.operation_error_with_reason,
                                operation,
                                e.message ?: context.getString(R.string.unknown_error),
                            )
                        ToastUtils.showShort(errorMessage)
                        LogUtils.e(
                            "${if (isEditMode) "UpdateRole" else "CreateRole"} error: ${e.message}"
                        )
                    }
                },
            )

            Spacer(modifier = Modifier.height(60.dp))
        }
    }
}

// Helper function to start UCrop with a local file
private fun startUCropWithLocalFile(
    sourceFile: File,
    context: Context,
    cropLauncher: ActivityResultLauncher<Intent>,
) {
    try {
        if (!sourceFile.exists() || sourceFile.length() == 0L) {
            ToastUtils.showShort(R.string.toast_image_file_not_found)
            return
        }

        val sourceUri = Uri.fromFile(sourceFile)
        val destinationFile = File(context.cacheDir, "cropped_avatar_${UUID.randomUUID()}.jpg")
        val destinationUri = Uri.fromFile(destinationFile)

        // Configure UCrop
        val cropIntent =
            UCrop.of(sourceUri, destinationUri)
                .withAspectRatio(1f, 1f) // Square aspect ratio for avatar
                .withMaxResultSize(512, 512) // Reasonable size for avatars
                .withOptions(
                    UCrop.Options().apply {
                        setCompressionQuality(90)
                        setHideBottomControls(true) // Hide bottom controls (rotate/scale buttons)
                        setFreeStyleCropEnabled(false)
                        setToolbarTitle(context.getString(R.string.crop_image))
                        setStatusBarColor("#1C1523".toColorInt())
                        setToolbarColor("#1C1523".toColorInt())
                        setActiveControlsWidgetColor("#E91E63".toColorInt())
                        setToolbarWidgetColor(AndroidColor.WHITE)
                        setCropFrameColor(AndroidColor.WHITE)
                        setCropGridColor(AndroidColor.WHITE)
                        setCircleDimmedLayer(true) // Enable circular cropping
                        setShowCropFrame(false) // Hide square frame for circular crop
                        setShowCropGrid(false) // Hide grid for cleaner circular crop
                        setAllowedGestures(
                            UCropActivity.SCALE,
                            UCropActivity.NONE,
                            UCropActivity.NONE,
                        ) // Only allow scaling gestures
                    }
                )
                .getIntent(context)

        cropLauncher.launch(cropIntent)
    } catch (e: Exception) {
        ToastUtils.showShort(R.string.toast_failed_open_crop_editor)
    }
}

@Composable
private fun AvatarUploadSection(
    avatarUrl: String?,
    avatarUrls: List<String> = emptyList(),
    selectedIndex: Int = 0,
    isGenerating: Boolean = false,
    croppedAvatarUrl: String? = null,
    onGenerateClick: () -> Unit,
    onImageSelected: (Int) -> Unit = {},
    onRegenerate: (String) -> Unit = {},
    onFaceEdit: () -> Unit = {},
) {
    val isEmpty = avatarUrls.isEmpty() && avatarUrl == null
    Column(modifier = Modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier =
                Modifier.then(
                        if (isEmpty) Modifier.size(200.dp)
                        else Modifier
                            .fillMaxWidth()
                            .aspectRatio(9.div(16f))
                    )
                    .let { modifier ->
                        if (isEmpty) {
                            modifier
                                .background(
                                    color = Color(0x1A78599A),
                                    shape = RoundedCornerShape(16.dp),
                                )
                                .noRippleClickable { onGenerateClick() }
                        } else {
                            modifier.background(
                                color = Color.Black,
                                shape = RoundedCornerShape(16.dp),
                            )
                        }
                    },
            contentAlignment = Alignment.Center,
        ) {
            when {
                isGenerating -> {
                    ThreeDotLoadingAnimation()
                }
                // 多选模式：AI生成了多个头像变体，用户可从中选择
                avatarUrls.isNotEmpty() -> {
                    val displayUrl = avatarUrls.getOrNull(selectedIndex) ?: avatarUrls.first()
                    val previewUrl =
                        getCdnImageUrl(
                            displayUrl,
                            width = Config.TextToImage.Preview.WIDTH,
                            quality = Config.TextToImage.Preview.QUALITY,
                        )
                    AsyncImage(
                        model = previewUrl ?: displayUrl,
                        contentDescription = stringResource(R.string.content_desc_selected_avatar),
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(RoundedCornerShape(8.dp)),
                        contentScale = ContentScale.Crop,
                        onSuccess = {
                            LogUtils.d(
                                "AvatarUploadSection: Selected avatar image loaded successfully: $displayUrl, preview: $previewUrl"
                            )
                        },
                        onError = {
                            LogUtils.e(
                                "AvatarUploadSection: Failed to load selected avatar image: $displayUrl"
                            )
                        },
                    )
                }
                // 单选模式：单个头像（编辑模式/用户上传/AI生成单个头像）
                avatarUrl != null -> {
                    LogUtils.d("AvatarUploadSection: Displaying single avatar with URL: $avatarUrl")

                    val previewUrl =
                        getCdnImageUrl(
                            avatarUrl,
                            width = Config.TextToImage.Preview.WIDTH,
                            quality = Config.TextToImage.Preview.QUALITY,
                        )
                    AsyncImage(
                        model = previewUrl ?: avatarUrl,
                        contentDescription = stringResource(R.string.content_desc_generated_avatar),
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(RoundedCornerShape(8.dp)),
                        contentScale = ContentScale.Crop,
                        onSuccess = {
                            LogUtils.d(
                                "AvatarUploadSection: Avatar image loaded successfully: $avatarUrl, preview: $previewUrl"
                            )
                        },
                        onError = {
                            LogUtils.e(
                                "AvatarUploadSection: Failed to load avatar image: $avatarUrl"
                            )
                        },
                    )
                }

                else -> {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Image(
                            painter = painterResource(R.drawable.btn_add),
                            contentDescription = null,
                            modifier = Modifier.size(48.dp),
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = stringResource(R.string.generate_avatar_title_full),
                            fontSize = 14.sp,
                            color = Color.White.copy(0.7f),
                            textAlign = TextAlign.Center,
                        )
                    }
                }
            }

            // Dashed border for empty state
            if (avatarUrls.isEmpty() && avatarUrl == null) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val strokeWidth = 1.dp.toPx()
                    val cornerRadius = 16.dp.toPx()
                    val dashLength = 10.dp.toPx()
                    val gapLength = 5.dp.toPx()

                    drawRoundRect(
                        color = Color.Gray,
                        topLeft = Offset(strokeWidth / 2, strokeWidth / 2),
                        size = Size(size.width - strokeWidth, size.height - strokeWidth),
                        cornerRadius = CornerRadius(cornerRadius),
                        style =
                            Stroke(
                                width = strokeWidth,
                                pathEffect =
                                    PathEffect.dashPathEffect(floatArrayOf(dashLength, gapLength)),
                            ),
                    )
                }
            }

            // Face edit button - show only when there's an avatar
            if (avatarUrls.isNotEmpty() || avatarUrl != null) {
                Box(
                    modifier =
                        Modifier
                            .align(Alignment.TopEnd)
                            .padding(8.dp)
                            .background(
                                color = Color.Black.copy(alpha = 0.5f),
                                shape = RoundedCornerShape(16.dp),
                            )
                            .noRippleClickable { onFaceEdit() }
                            .padding(horizontal = 12.dp, vertical = 6.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Image(
                            painter = painterResource(R.drawable.ic_crop),
                            contentDescription = stringResource(R.string.face_edit),
                            modifier = Modifier.size(16.dp),
                        )
                        Text(
                            text = stringResource(R.string.face_edit),
                            color = Color.White,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                        )
                    }
                }
            }
        }
        Spacer(Modifier.height(8.dp))
        // 底部一行，生成的ai模型的照片图像 Floating thumbnail row at the bottom of preview
        if (avatarUrls.isNotEmpty()) {
            Row(
                modifier =
                    Modifier
                        .fillMaxWidth()
                        .background(
                            color = Color.Black.copy(alpha = 0.5f),
                            shape = RoundedCornerShape(12.dp),
                        )
                        .padding(12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // Fixed Regen button on the left
                Box(
                    modifier = Modifier
                        .width(88.dp)
                        .aspectRatio(9 / 16f)
                ) {
                    RegenButton(
                        onClick = { onRegenerate(AvatarManager.getGenerationPrompt()) },
                        enabled = !isGenerating,
                    )
                }

                // Scrollable thumbnail row
                LazyRow(
                    modifier = Modifier.weight(1f),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    runCatching {
                            if (avatarUrls.isNotEmpty()) {
                                items(items = avatarUrls.indices.toList()) { index ->
                                    val imageUrl = avatarUrls[index]
                                    // 使用 CDN 裁切获取缩略图，使用配置的宽度和质量
                                    val thumbnailUrl =
                                        getCdnImageUrl(imageUrl, width = 80, quality = 60)
                                    Box(
                                        modifier =
                                            Modifier
                                                .width(88.dp)
                                                .aspectRatio(9 / 16f)
                                                .background(
                                                    color = Color(0x1A78599A),
                                                    shape = RoundedCornerShape(8.dp),
                                                )
                                                .border(
                                                    width =
                                                        if (index == selectedIndex) 3.dp else 1.dp,
                                                    color =
                                                        if (index == selectedIndex)
                                                            Color(0xFFE91E63)
                                                        else Color.Transparent,
                                                    shape = RoundedCornerShape(8.dp),
                                                )
                                                .noRippleClickable { onImageSelected(index) },
                                        contentAlignment = Alignment.Center,
                                    ) {
                                        AsyncImage(
                                            model = thumbnailUrl ?: imageUrl, // 如果 CDN 处理失败，回退到原图
                                            contentDescription =
                                                stringResource(
                                                    R.string.content_desc_generated_avatar_index,
                                                    index,
                                                ),
                                            modifier =
                                                Modifier
                                                    .fillMaxSize()
                                                    .clip(RoundedCornerShape(8.dp)),
                                            contentScale = ContentScale.Crop,
                                        )
                                    }
                                }
                            }
                        }
                        .onFailure { it.printStackTrace() }
                }
            }
        }
    }
}

@Composable
private fun GenderSelectionSection(selectedGender: String, onGenderChange: (String) -> Unit) {
    Column {
        Text(
            text = stringResource(R.string.gender_unmodified_full),
            fontSize = 16.sp,
            color = Color.White,
            fontWeight = FontWeight.Medium,
        )
        Spacer(modifier = Modifier.height(12.dp))

        Row(
            horizontalArrangement = Arrangement.spacedBy(4.dp),
            modifier = Modifier.fillMaxWidth(),
        ) {
            GenderButton(
                text = stringResource(R.string.male_full),
                isSelected = selectedGender == "MALE",
                onClick = { onGenderChange("MALE") },
                modifier = Modifier.weight(0.8f),
            )
            GenderButton(
                text = stringResource(R.string.female_full),
                isSelected = selectedGender == "FEMALE",
                onClick = { onGenderChange("FEMALE") },
                modifier = Modifier.weight(0.9f),
            )
            GenderButton(
                text = stringResource(R.string.non_binary_full),
                isSelected = selectedGender == "NON_BINARY",
                onClick = { onGenderChange("NON_BINARY") },
                modifier = Modifier.weight(1.1f),
            )
        }
    }
}

@Composable
private fun CustomTextField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    minLines: Int = 1,
    maxLength: Int = 500,
) {
    Column {
        Text(text = label, fontSize = 16.sp, color = Color.White, fontWeight = FontWeight.Medium)
        Spacer(modifier = Modifier.height(12.dp))
        MultiLineBasicTextField(
            value = value,
            onValueChange = onValueChange,
            placeholder = placeholder,
            minLines = minLines,
            maxLength = maxLength
        )
    }
}

@Composable
private fun GenderButton(
    text: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    var lastClickTime by remember { mutableLongStateOf(0L) }

    Button(
        onClick = {
            val currentTime = System.currentTimeMillis()
            if (AntiClick.isValidClick(lastClickTime)) {
                lastClickTime = currentTime
                onClick()
            }
        },
        colors = ButtonDefaults.buttonColors(containerColor = Color(0x1A78599A)),
        shape = RoundedCornerShape(20.dp),
        modifier =
            modifier.border(
                width = if (isSelected) 2.dp else 1.dp,
                color = if (isSelected) Color(0xFFE91E63) else Color.White.copy(0.3f),
                shape = RoundedCornerShape(20.dp),
            ),
    ) {
        Text(
            text = text,
            fontSize = 12.sp,
            color = Color.White,
            modifier = Modifier.padding(horizontal = 2.dp, vertical = 4.dp),
        )
    }
}

@Composable
private fun CreateButton(isLoading: Boolean, isEditMode: Boolean = false, onClick: () -> Unit) {
    var lastClickTime by remember { mutableLongStateOf(0L) }

    Button(
        onClick = {
            val currentTime = System.currentTimeMillis()
            if (AntiClick.isValidClick(lastClickTime)) {
                lastClickTime = currentTime
                onClick()
            }
        },
        enabled = !isLoading,
        colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
        shape = RoundedCornerShape(25.dp),
        modifier =
            Modifier
                .fillMaxWidth()
                .height(56.dp)
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors = listOf(Color(0xFFE91E63), Color(0xFFFF9800))
                        ),
                    shape = RoundedCornerShape(25.dp),
                ),
    ) {
        if (isLoading) {
            CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
        } else {
            Text(
                text = if (isEditMode) "Update My IntelliMate" else "Create My IntelliMate",
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
        }
    }
}

/**
 * Configuration object for text-to-image preview settings
 *
 * @GeneratedByAI - AI generated configuration for image scaling parameters
 */
object Config {
    object TextToImage {
        object Preview {
            /** Preview image width for CDN scaling */
            const val WIDTH = 400

            /** Preview image quality for CDN scaling (0-100) */
            const val QUALITY = 60
        }
    }
}
