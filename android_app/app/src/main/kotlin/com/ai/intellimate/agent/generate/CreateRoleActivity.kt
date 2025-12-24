package com.ai.intellimate.agent.generate

import ai.sxwl.android.common.base.BaseActivity
import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.design.AntiClick
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import android.app.Activity
import android.content.ContentResolver
import android.content.Context
import android.content.Intent
import android.graphics.Color as AndroidColor
import android.net.Uri
import android.os.Build
import android.provider.OpenableColumns
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
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
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Flag
import androidx.compose.material.icons.outlined.Upload
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
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
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
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
import coil3.SingletonImageLoader
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import coil3.request.SuccessResult
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.ui.NameInputKeyBoardOption
import com.ai.intellimate.ui.SingleLineInputField
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.utils.AvatarManager
import com.ai.intellimate.utils.UCropHelper
import com.ai.intellimate.xb.components.IgnoreSystemFontScaling
import com.ai.intellimate.xb.components.MultiLineBasicTextField
import com.yalantis.ucrop.UCrop
import com.yalantis.ucrop.UCropActivity
import java.io.File
import java.io.FileOutputStream
import java.util.Locale
import java.util.UUID
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** 创建角色的页面 */
class CreateRoleActivity : BaseActivity() {

    companion object {
        private const val INTENT_KEY_AGENT_INFO = "intent_key_agent_info"
        private const val INTENT_KEY_DRAFT_ID = "intent_key_draft_id"

        /**
         * 启动创建/编辑角色界面
         *
         * @param context 上下文context
         * @param agentInfo Agent的Info对象，为null时表示创建新角色，否则表示编辑现有角色
         * @param draftId 草稿ID，如果提供则从草稿列表加载该草稿；UUID 字符串
         */
        fun launch(context: Context, agentInfo: AgentInfo? = null, draftId: String? = null) {
            context.startActivity(
                Intent(context, CreateRoleActivity::class.java).also { intent ->
                    intent.putExtra(INTENT_KEY_AGENT_INFO, agentInfo)
                    draftId?.let { intent.putExtra(INTENT_KEY_DRAFT_ID, it) }
                }
            )
        }

        /**
         * 获取创建/编辑角色界面的 Intent（用于 Activity Result）
         *
         * @param context 上下文context
         * @param agentInfo Agent的Info对象，为null时表示创建新角色，否则表示编辑现有角色
         * @param draftId 草稿ID，如果提供则从草稿列表加载该草稿；UUID 字符串
         * @return 配置好的 Intent
         */
        fun getIntent(
            context: Context,
            agentInfo: AgentInfo? = null,
            draftId: String? = null,
        ): Intent {
            return Intent(context, CreateRoleActivity::class.java).apply {
                putExtra(INTENT_KEY_AGENT_INFO, agentInfo)
                draftId?.let { putExtra(INTENT_KEY_DRAFT_ID, it) }
            }
        }
    }

    private var agent: AgentInfo? = null
    private var draftId: String? = null
    private val createRoleViewModel: CreateRoleViewModel by viewModels()

    override fun initConfigData() {
        super.initConfigData()
        agent =
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(INTENT_KEY_AGENT_INFO, AgentInfo::class.java)
            } else {
                @Suppress("DEPRECATION") intent.getParcelableExtra(INTENT_KEY_AGENT_INFO)
            }
        draftId = intent.getStringExtra(INTENT_KEY_DRAFT_ID)
    }

    @Composable
    override fun ConfigComposeUI() {
        super.ConfigComposeUI()
        CreateRolePage(
            modifier = Modifier.fillMaxSize(),
            createRoleViewModel = createRoleViewModel,
            onBack = { finish() },
            onCreateSuccess = {
                setResult(RESULT_OK)
                finish()
            },
            onAvatarGenerateClick = { prompt ->
                AvatarGenerateActivity.launch(this, prompt?.takeIf { it.isNotBlank() })
            },
            editAgent = agent,
            draftId = draftId,
        )
    }
}

private const val MAX_GALLERY_PHOTO_SIZE_MB = 2
private val DraftDialogConfirmColor = Color(0xFF7C56FF)
private val DraftDialogDismissColor = Color(0xFF3A2D40)
private val DraftDialogContainerColor = Color(0xFF2A2A2A)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun CreateRolePage(
    modifier: Modifier = Modifier,
    createRoleViewModel: CreateRoleViewModel,
    onBack: () -> Unit,
    onCreateSuccess: () -> Unit,
    onAvatarGenerateClick: (String?) -> Unit,
    editAgent: AgentInfo? = null,
    draftId: String? = null,
) {
    val isEditMode = editAgent != null
    val savedDraft =
        remember(editAgent, draftId) {
            when {
                editAgent != null -> null
                draftId != null -> CreateRoleDraftStorage.getDraftById(draftId)
                else -> CreateRoleDraftStorage.loadCurrentDraft()
            }
        }
    var latestDraft by remember(savedDraft) { mutableStateOf(savedDraft ?: CreateRoleDraft()) }
    var enableDraftSaving by remember { mutableStateOf(true) }
    var showSaveDraftDialog by remember { mutableStateOf(false) }

    val nameInitial =
        if (isEditMode) {
            editAgent.name
        } else {
            savedDraft?.name.orEmpty()
        }
    var name by remember(nameInitial) { mutableStateOf(nameInitial) }

    val genderInitial =
        if (isEditMode) {
            editAgent.gender
        } else {
            savedDraft?.gender ?: CreateRoleDraft.DEFAULT_GENDER
        }
    var gender by remember(genderInitial) { mutableStateOf(genderInitial) }

    val editSettings = editAgent?.settings?.get("description") as? String ?: editAgent?.prompt ?: ""
    val settingsInitial = if (isEditMode) editSettings else savedDraft?.settings.orEmpty()
    var settings by remember(settingsInitial) { mutableStateOf(settingsInitial) }

    val introInitial =
        if (isEditMode) {
            editAgent.intro
        } else {
            savedDraft?.intro.orEmpty()
        }
    var intro by remember(introInitial) { mutableStateOf(introInitial) }

    val openingInitial =
        if (isEditMode) {
            editAgent.opening
        } else {
            savedDraft?.opening.orEmpty()
        }
    var opening by remember(openingInitial) { mutableStateOf(openingInitial) }

    val visibilityInitial =
        if (isEditMode) {
            editAgent.visibility
        } else {
            savedDraft?.visibility ?: CreateRoleDraft.DEFAULT_VISIBILITY
        }
    var visibility by remember(visibilityInitial) { mutableStateOf(visibilityInitial) }

    var isLoading by remember { mutableStateOf(false) }

    val editAvatarUrls = if (isEditMode) editAgent.backgroundImages else emptyList()
    val avatarUrlsInitial =
        if (isEditMode) editAvatarUrls
        else savedDraft?.avatarUrls?.filter { it.isNotBlank() } ?: emptyList()
    var avatarUrls by remember(avatarUrlsInitial) { mutableStateOf(avatarUrlsInitial) }

    val editSingleBackground =
        if (isEditMode && editAgent.backgroundImages.isEmpty()) {
            editAgent.background.takeIf { it.isNotBlank() }
        } else {
            null
        }
    val avatarUrlInitial =
        if (avatarUrlsInitial.isNotEmpty()) {
            null
        } else if (isEditMode) {
            editSingleBackground
        } else {
            savedDraft?.avatarUrl?.takeIf { it.isNotBlank() }
        }
    var avatarUrl by remember(avatarUrlInitial) { mutableStateOf(avatarUrlInitial) }

    val editSelectedIndex =
        if (isEditMode && editAgent.backgroundImages.isNotEmpty()) {
            val backgroundUrl = editAgent.background.takeIf { it.isNotBlank() }
            backgroundUrl?.let { url ->
                val index = editAgent.backgroundImages.indexOf(url)
                if (index >= 0) index else 0
            } ?: 0
        } else {
            0
        }
    val savedSelectedIndex =
        savedDraft?.selectedImageIndex?.let { draftIndex ->
            val lastIndex = avatarUrlsInitial.lastIndex
            if (lastIndex < 0) 0 else draftIndex.coerceIn(0, lastIndex)
        } ?: 0
    var selectedImageIndex by
        remember(isEditMode, avatarUrlsInitial, editSelectedIndex, savedSelectedIndex) {
            mutableIntStateOf(if (isEditMode) editSelectedIndex else savedSelectedIndex)
        }
    var isGeneratingAvatar by remember { mutableStateOf(false) }
    val editCroppedAvatar =
        if (isEditMode) editAgent.avatar.takeIf { it.isNotBlank() && it != editAgent.background }
        else null
    val croppedInitial =
        if (isEditMode) editCroppedAvatar else savedDraft?.croppedAvatarUrl
    var croppedAvatarUrl by remember(croppedInitial) { mutableStateOf(croppedInitial) }
    val avatarPromptInitial = if (isEditMode) "" else savedDraft?.avatarPrompt.orEmpty()
    var avatarPrompt by remember(avatarPromptInitial) { mutableStateOf(avatarPromptInitial) }

    // 当 selectedImageIndex 改变时，将 croppedAvatarUrl 设置为空
    LaunchedEffect(Unit) {
        snapshotFlow { selectedImageIndex }
            .drop(1) // 跳过初始值，只在真正改变时触发
            .collect { croppedAvatarUrl = null }
    }

    // Track original uploaded image URL (for background) when uploading from gallery
    var originalUploadedImageUrl by remember { mutableStateOf<String?>(null) }
    var isUploadingFromGallery by remember { mutableStateOf(false) }

    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val focusManager = LocalFocusManager.current
    val hasDraftChanges = !latestDraft.isEmpty()
    val handleExitRequest = {
        if (isEditMode || !hasDraftChanges) {
            onBack()
        } else if (savedDraft != null) {
            // 从 draft 进入，更新草稿列表中的草稿，清除临时草稿，然后退出
            val draftToSave = latestDraft.copy(id = savedDraft.id, createdAt = savedDraft.createdAt)
            CreateRoleDraftStorage.saveDraftToList(draftToSave)
            CreateRoleDraftStorage.clearCurrentDraft()
            onBack()
        } else {
            showSaveDraftDialog = true
        }
    }

    if (!isEditMode) {
        BackHandler { handleExitRequest() }
    }

    if (!isEditMode) {
        LaunchedEffect(enableDraftSaving) {
            if (!enableDraftSaving) return@LaunchedEffect
            snapshotFlow {
                    val normalizedUrls = avatarUrls.filter { it.isNotBlank() }
                    val sanitizedIndex =
                        if (normalizedUrls.isEmpty()) 0
                        else selectedImageIndex.coerceIn(0, normalizedUrls.lastIndex)
                    CreateRoleDraft(
                        name = name,
                        gender = gender,
                        settings = settings,
                        intro = intro,
                        opening = opening,
                        visibility = visibility,
                        avatarUrl = avatarUrl?.takeIf { it.isNotBlank() },
                        avatarUrls = normalizedUrls,
                        selectedImageIndex = sanitizedIndex,
                        croppedAvatarUrl = croppedAvatarUrl?.takeIf { it.isNotBlank() },
                        avatarPrompt = avatarPrompt,
                    )
                }
                .distinctUntilChanged()
                .collect { draft ->
                    latestDraft = draft
                    // 自动保存到临时草稿
                    CreateRoleDraftStorage.saveCurrentDraft(draft)
                }
        }
    }
    // Clear avatar data when creating new character
    LaunchedEffect(isEditMode) {
        if (!isEditMode) {
            AvatarManager.clearAllAvatarData()
            avatarPrompt = savedDraft?.avatarPrompt.orEmpty()
            LogUtils.i("Cleared avatar data for new character creation")
        }
    }

    // Clean up AvatarManager when leaving the activity
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_STOP -> {
                    // Clear AvatarManager when activity is stopped (user navigates away)
                    // LogUtils.i("Activity stopped - clearing AvatarManager data")
                    // AvatarManager.clearAllAvatarData()
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

    // 使用 snapshotFlow 监听生命周期状态变化，在组合周期内安全地更新状态
    // 当活动销毁时清除图库上传标志，防止状态过期
    // 注意：不在 CREATED 状态清除，因为从 UCrop 返回时可能经过 CREATED，会过早清除标志
    LaunchedEffect(lifecycleOwner) {
        snapshotFlow { lifecycleOwner.lifecycle.currentState }
            .collect { state ->
                when (state) {
                    Lifecycle.State.DESTROYED -> {
                        // 活动销毁时清除标志
                        LogUtils.i("Activity lifecycle DESTROYED: clearing gallery upload flags")
                        isUploadingFromGallery = false
                        originalUploadedImageUrl = null
                    }
                    else -> {}
                }
            }
    }

    // UCrop launcher for avatar cropping
    val cropLauncher =
        rememberLauncherForActivityResult(
            contract = ActivityResultContracts.StartActivityForResult()
        ) { result ->
            when (result.resultCode) {
                Activity.RESULT_OK -> {
                    result.data?.let { data ->
                        croppedAvatarUrl = UCrop.getOutput(data)?.toString()
                    }
                }
                UCrop.RESULT_ERROR -> {
                    result.data?.let { data ->
                        val cropError = UCrop.getError(data)
                        LogUtils.e("UCrop error: ${cropError?.message}")
                        isUploadingFromGallery = false
                        originalUploadedImageUrl = null
                        ToastUtils.showShort(
                            context.getString(R.string.toast_crop_failed, cropError?.message ?: "")
                        )
                    }
                }
                Activity.RESULT_CANCELED -> {
                    // 用户取消了裁剪操作（按返回键），清除图库上传标志
                    LogUtils.i("Crop operation cancelled by user")
                    isUploadingFromGallery = false
                    originalUploadedImageUrl = null
                }
                else -> {
                    // 处理其他未知结果代码，确保清除标志
                    LogUtils.w("Unknown crop result code: ${result.resultCode}")
                    isUploadingFromGallery = false
                    originalUploadedImageUrl = null
                }
            }
        }

    // Gallery launcher for selecting image from phone
    val galleryLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { imageUri ->
            imageUri?.let { uri ->
                val fileSize = getFileSize(context, uri)
                val maxSizeBytes = MAX_GALLERY_PHOTO_SIZE_MB * 1024 * 1024L
                if (fileSize == 0L) {
                    ToastUtils.showShort(
                        context.getString(
                            R.string.toast_failed_prepare_upload_with_message,
                            "Unable to determine file size",
                        )
                    )
                    return@let
                }

                if (fileSize > maxSizeBytes) {
                    val maxSizeMBStr =
                        String.format(Locale.getDefault(), "%dMB", MAX_GALLERY_PHOTO_SIZE_MB)
                    val fileSizeMBStr =
                        String.format(Locale.getDefault(), "%.1fMB", fileSize / (1024.0 * 1024.0))
                    val msg =
                        context.getString(
                            R.string.user_avatar_size_too_large_with_size_format,
                            maxSizeMBStr,
                            fileSizeMBStr,
                        )
                    ToastUtils.showShort(msg)
                    return@let
                }

                runCatching {
                        val copiedFile = copyUriToTempFile(context, uri)
                        val finalUri =
                            if (copiedFile != null) {
                                LogUtils.i(
                                    "Image copied to private directory: ${copiedFile.absolutePath}"
                                )
                                Uri.fromFile(copiedFile)
                            } else {
                                throw Exception("Failed to copy image to private directory")
                            }

                        val historyImageSize = avatarUrls.size

                        avatarUrls += finalUri.toString()
                        selectedImageIndex = historyImageSize
                        // Launch UCrop with the original URI
                        val intentCrop =
                            UCropHelper.getIntent(
                                context,
                                finalUri,
                                context.getString(R.string.crop_image),
                            )
                        cropLauncher.launch(intentCrop)
                    }
                    .onFailure { e ->
                        LogUtils.e("Gallery selection error: ${e.message}")
                        isUploadingFromGallery = false
                        ToastUtils.showShort(
                            context.getString(
                                R.string.toast_failed_prepare_upload_with_message,
                                e.message ?: "Unknown error",
                            )
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
            val promptDraft = AvatarManager.getGenerationPrompt()
            if (generatingStatus) {
                LogUtils.i("Currently generating with prompt: '$promptDraft'")
            }
            if (promptDraft.isNotBlank() && promptDraft != avatarPrompt) {
                avatarPrompt = promptDraft
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
                val promptDraft = AvatarManager.getGenerationPrompt()
                if (promptDraft.isNotBlank() && promptDraft != avatarPrompt) {
                    avatarPrompt = promptDraft
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

            val promptDraft = AvatarManager.getGenerationPrompt()
            if (promptDraft.isNotBlank() && promptDraft != avatarPrompt) {
                avatarPrompt = promptDraft
            }
        }
    }

    Scaffold(
        modifier = modifier.background(HeartColor.primaryColor),
        containerColor = HeartColor.primaryColor,
        topBar = {
            CenterAlignedTopAppBar(
                colors =
                    TopAppBarDefaults.topAppBarColors()
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
                            Modifier.padding(horizontal = 12.dp).noRippleClickable {
                                handleExitRequest()
                            },
                        painter = painterResource(R.drawable.close),
                        contentDescription = null,
                    )
                },
            )
        },
    ) { padding ->
        Column(
            modifier =
                Modifier.fillMaxSize()
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
            // 视觉形象编辑区域标题
            Text(
                text = "Visual Appearance",
                fontSize = 16.sp,
                color = Color.White,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.fillMaxWidth(),
                textAlign = TextAlign.Start,
            )

            val promptForGeneration = avatarPrompt.ifBlank { settings }

            AvatarUploadSection(
                avatarUrl = avatarUrl,
                avatarUrls = avatarUrls,
                selectedIndex = selectedImageIndex,
                isGenerating = isGeneratingAvatar,
                isUploadingGallery = isUploadingFromGallery,
                croppedAvatarUrl = croppedAvatarUrl,
                agentId = editAgent?.id,
                onGenerateClick = {
                    AvatarManager.setGeneratedAvatarUrls(avatarUrls)
                    AvatarManager.setSelectedImageIndex(selectedImageIndex)

                    onAvatarGenerateClick(promptForGeneration.takeIf { it.isNotBlank() })
                    // 当点击生成头像时，不清除当前URL，让用户返回时检查新的URL
                },
                onImageSelected = { index ->
                    selectedImageIndex = index
                    AvatarManager.setSelectedImageIndex(index)
                },
                onRegenerate = { prompt ->
                    AvatarManager.setGeneratedAvatarUrls(avatarUrls)
                    AvatarManager.setSelectedImageIndex(selectedImageIndex)

                    // Navigate to avatar generation page with existing prompt
                    val promptToUse = prompt.takeIf { it.isNotBlank() } ?: promptForGeneration
                    onAvatarGenerateClick(promptToUse.takeIf { it.isNotBlank() })
                },
                onRemoveImage = { index ->
                    if (avatarUrls.isEmpty() || index !in avatarUrls.indices) {
                        return@AvatarUploadSection
                    }

                    val updatedList = avatarUrls.toMutableList().apply { removeAt(index) }
                    val newIndex =
                        if (updatedList.isEmpty()) {
                            0
                        } else {
                            when {
                                index < selectedImageIndex && selectedImageIndex > 0 -> {
                                    (selectedImageIndex - 1).coerceAtMost(updatedList.lastIndex)
                                }
                                selectedImageIndex >= updatedList.size -> updatedList.lastIndex
                                else -> selectedImageIndex.coerceIn(0, updatedList.lastIndex)
                            }
                        }

                    avatarUrls = updatedList
                    selectedImageIndex = newIndex

                    AvatarManager.setGeneratedAvatarUrls(updatedList)
                    AvatarManager.setSelectedImageIndex(newIndex)
                },
                onFaceEdit = faceEdit@{
                        AvatarManager.clearAllAvatarData()

                        // Get the current avatar URL to crop
                        val imageUrl =
                            if (avatarUrls.isNotEmpty()) {
                                // Defensive bounds checking
                                val safeIndex =
                                    if (
                                        selectedImageIndex >= 0 &&
                                            selectedImageIndex < avatarUrls.size
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

                        if (imageUrl.isNullOrBlank()) {
                            ToastUtils.showShort(R.string.toast_no_avatar_image)
                            return@faceEdit
                        }

                        if (
                            tryStartCropWithLocalImage(
                                context = context,
                                imageUrl = imageUrl,
                                cropLauncher = cropLauncher,
                            )
                        ) {
                            return@faceEdit
                        }

                        val previewUrl =
                            getCdnImageUrl(
                                originUrl = imageUrl,
                                width = Config.TextToImage.Preview.WIDTH,
                                quality = Config.TextToImage.Preview.QUALITY,
                            )

                        createRoleViewModel.viewModelScope.launch(Dispatchers.IO) {
                            try {
                                val imageLoader = SingletonImageLoader.get(context)
                                val request =
                                    ImageRequest.Builder(context)
                                        .data(previewUrl ?: imageUrl)
                                        .build()
                                val result = imageLoader.execute(request)

                                if (result is SuccessResult) {
                                    val snapshot =
                                        result.diskCacheKey?.let { key ->
                                            imageLoader.diskCache?.openSnapshot(key)
                                        }

                                    if (snapshot != null) {
                                        snapshot.use {
                                            startUCropWithLocalFile(
                                                it.data.toFile(),
                                                context,
                                                cropLauncher,
                                            )
                                        }
                                    } else {
                                        withContext(Dispatchers.Main) {
                                            ToastUtils.showShort(
                                                R.string.toast_failed_download_image_editing
                                            )
                                        }
                                    }
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
                    },
                onUploadFromGallery = { galleryLauncher.launch("image/*") },
            )

            // Spacer(modifier = Modifier.height(24.dp))
            // 该间距并不需要，显示效果不影响该有的间距。
            SingleLineInputField(
                value = name,
                onValueChange = { name = it },
                keyboardOptions = NameInputKeyBoardOption,
                title = "Name *",
                placeholder = "Name your IntelliMate",
            )

            // Gender Selection 已经创建后的，也就是在修改模式下，性别选项则不显示
            if (!isEditMode) {
                Spacer(modifier = Modifier.height(24.dp))
                GenderSelectionSection(selectedGender = gender, onGenderChange = { gender = it })
            }

            Spacer(modifier = Modifier.height(24.dp))

            VisibilitySwitchSection(
                isPublic = visibility == "PUBLIC",
                onPublicChange = { isPublic ->
                    visibility = if (isPublic) "PUBLIC" else "PRIVATE"
                },
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Settings Field
            CustomTextField(
                label = "Core Settings (determines dialogue effect) *",
                value = settings,
                onValueChange = { settings = it },
                placeholder = "Please fill in the dialogue effect...",
                minLines = 2,
                maxLength = 800,
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Opening Field
            CustomTextField(
                label = "Opening (set tone and context) *",
                value = opening,
                onValueChange = { opening = it },
                placeholder = "Please fill in the character's opening remarks...",
                minLines = 2,
                maxLength = 200,
            )

            Spacer(modifier = Modifier.height(24.dp))

            // Intro Field
            CustomTextField(
                label = "Intro for other users (no impact on chat) *",
                value = intro,
                onValueChange = { intro = it },
                placeholder = "Please fill in the character introduction...",
                minLines = 2,
                maxLength = 500,
            )

            Spacer(modifier = Modifier.height(40.dp))

            val scope = rememberCoroutineScope()

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

                    isLoading = true

                    scope
                        .launch {
                            try {
                                // Prepare avatar and background fields according to new logic
                                val backgroundUrl =
                                    if (avatarUrls.isNotEmpty()) {
                                        // Use selected image from generated grid as background
                                        avatarUrls.getOrNull(selectedImageIndex)
                                            ?: avatarUrls.first()
                                    } else {
                                        // Use single generated image as background
                                        avatarUrl
                                    }

                                val backgroundImagesList =
                                    avatarUrls.ifEmpty { listOfNotNull(avatarUrl) }

                                // Save background for chat usage
                                if (backgroundUrl != null) {
                                    AvatarManager.setChatBackgroundUrl(backgroundUrl)
                                }

                                val request =
                                    CreateAgentRequest(
                                        name = name,
                                        gender = gender,
                                        avatar =
                                            croppedAvatarUrl
                                                ?: editAgent?.avatar?.takeIf {
                                                    editAgent.background == backgroundUrl
                                                },
                                        background = backgroundUrl,
                                        backgroundImages = backgroundImagesList,
                                        settings = mapOf("description" to settings),
                                        intro = intro,
                                        opening = opening,
                                        visibility = visibility,
                                        prompt = settings,
                                    )

                                // Call API through ViewModel
                                createRoleViewModel.updateAgent(
                                    agentId = editAgent?.id.takeIf { isEditMode },
                                    request = request,
                                    createTempFile = { context.createTempFile(it) },
                                    context = context,
                                )

                                if (isEditMode) {
                                    ToastUtils.showShort(R.string.character_updated_successfully)
                                    onCreateSuccess()
                                } else {
                                    // 如果是从草稿列表进入的，删除该草稿
                                    if (savedDraft != null && draftId != null) {
                                        CreateRoleDraftStorage.deleteDraft(draftId)
                                    }
                                    // 清除临时草稿
                                    CreateRoleDraftStorage.clearCurrentDraft()
                                    ToastUtils.showShort(
                                        context.getString(R.string.create_ai_successfully)
                                    )
                                    onCreateSuccess()
                                }
                            } catch (e: Exception) {
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
                        }
                        .invokeOnCompletion { isLoading = false }
                },
            )

            Spacer(modifier = Modifier.height(60.dp))
        }
    }

    if (showSaveDraftDialog) {
        AlertDialog(
            onDismissRequest = { showSaveDraftDialog = false },
            title = {
                Text(
                    text = stringResource(R.string.save_draft_dialog_title),
                    color = Color.White,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            },
            text = {
                Text(
                    text = stringResource(R.string.save_draft_dialog_message),
                    color = Color.White.copy(alpha = 0.8f),
                    fontSize = 14.sp,
                    lineHeight = 20.sp,
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        // 保存到草稿列表（如果是新草稿会自动生成ID，如果是从草稿列表进入的会更新）
                        val draftToSave =
                            if (savedDraft != null) {
                                latestDraft.copy(
                                    id = savedDraft.id,
                                    createdAt = savedDraft.createdAt,
                                )
                            } else {
                                latestDraft
                            }
                        CreateRoleDraftStorage.saveDraftToList(draftToSave)
                        // 清除临时草稿，以便下次进入时创建新角色
                        CreateRoleDraftStorage.clearCurrentDraft()
                        showSaveDraftDialog = false
                        onBack()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = DraftDialogConfirmColor),
                ) {
                    Text(
                        text = stringResource(R.string.save_draft_dialog_confirm),
                        color = Color.White,
                        fontSize = 14.sp,
                    )
                }
            },
            dismissButton = {
                Button(
                    onClick = {
                        enableDraftSaving = false
                        // 清除临时草稿
                        CreateRoleDraftStorage.clearCurrentDraft()
                        showSaveDraftDialog = false
                        onBack()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = DraftDialogDismissColor),
                ) {
                    Text(
                        text = stringResource(R.string.save_draft_dialog_discard),
                        color = Color.White,
                        fontSize = 14.sp,
                    )
                }
            },
            containerColor = DraftDialogContainerColor,
        )
    }
}

// Helper function to get file size from URI
// Uses ContentResolver.query() with OpenableColumns.SIZE for reliable file size
private fun getFileSize(context: Context, uri: Uri): Long {
    return try {
        // First, try to get size from ContentResolver query (most reliable for content URIs)
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val sizeIndex = cursor.getColumnIndex(OpenableColumns.SIZE)
            if (sizeIndex != -1 && cursor.moveToFirst()) {
                val size = cursor.getLong(sizeIndex)
                if (size > 0) {
                    return size
                }
            }
        }

        // Fallback: For file URIs, try File.length()
        if (uri.scheme == "file") {
            uri.path?.let { path ->
                val file = File(path)
                if (file.exists()) {
                    return file.length()
                }
            }
        }

        // Last resort: Read the stream and count bytes (less efficient but works as fallback)
        context.contentResolver.openInputStream(uri)?.use { input ->
            var totalBytes = 0L
            val buffer = ByteArray(8192)
            var bytesRead: Int
            while (input.read(buffer).also { bytesRead = it } != -1) {
                totalBytes += bytesRead
            }
            return totalBytes
        } ?: 0L
    } catch (e: Exception) {
        LogUtils.e("Failed to get file size: ${e.message}")
        0L
    }
}

private fun Context.createTempFile(uri: Uri): File {
    // Check file size before processing - keep consistent with gallery limit
    val fileSize = getFileSize(this, uri)
    val maxSizeMB = MAX_GALLERY_PHOTO_SIZE_MB
    val maxSizeBytes = maxSizeMB * 1024 * 1024L

    // 如果无法确定文件大小（返回 0），拒绝上传以确保安全
    if (fileSize == 0L) {
        throw Exception(
            getString(
                R.string.toast_failed_prepare_upload_with_message,
                "Unable to determine file size",
            )
        )
    }

    if (fileSize > maxSizeBytes) {
        val maxSizeMBStr = String.format(Locale.getDefault(), "%dMB", maxSizeMB)
        val fileSizeMBStr =
            String.format(Locale.getDefault(), "%.1fMB", fileSize / (1024.0 * 1024.0))

        throw Exception(
            getString(
                R.string.user_avatar_size_too_large_with_size_format,
                maxSizeMBStr,
                fileSizeMBStr,
            )
        )
    }

    // Copy URI to temp file for upload
    val tempFile =
        copyUriToTempFile(this, uri)
            ?: throw Exception(
                getString(
                    R.string.toast_failed_prepare_upload_with_message,
                    "Failed to read image file",
                )
            )

    // 验证临时文件大小（双重检查，确保文件大小限制）
    val tempFileSize = tempFile.length()
    if (tempFileSize > maxSizeBytes) {
        val maxSizeMBStr = String.format(Locale.getDefault(), "%dMB", maxSizeMB)
        val fileSizeMBStr =
            String.format(Locale.getDefault(), "%.1fMB", tempFileSize / (1024.0 * 1024.0))

        throw Exception(
            getString(
                R.string.user_avatar_size_too_large_with_size_format,
                maxSizeMBStr,
                fileSizeMBStr,
            )
        )
    }

    return tempFile
}

// Helper function to copy URI to temporary file
private fun copyUriToTempFile(context: Context, uri: Uri): File? {
    return try {
        val tempFile = File(context.cacheDir, "temp_gallery_${UUID.randomUUID()}.jpg")
        context.contentResolver.openInputStream(uri)?.use { input ->
            FileOutputStream(tempFile).use { output -> input.copyTo(output) }
        }
        if (tempFile.exists() && tempFile.length() > 0) {
            tempFile
        } else {
            null
        }
    } catch (e: Exception) {
        LogUtils.e("Failed to copy URI to temp file: ${e.message}")
        null
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
        LogUtils.e("Failed to start UCrop, error: $e")
        ToastUtils.showShort(R.string.toast_failed_open_crop_editor)
    }
}

private fun tryStartCropWithLocalImage(
    context: Context,
    imageUrl: String,
    cropLauncher: ActivityResultLauncher<Intent>,
): Boolean {
    val imageUri = runCatching { imageUrl.toUri() }.getOrNull() ?: return false
    return when (imageUri.scheme?.lowercase(Locale.getDefault()) ?: ContentResolver.SCHEME_FILE) {
        ContentResolver.SCHEME_FILE -> {
            val localFile = imageUri.path?.let { File(it) }
            if (localFile != null && localFile.exists() && localFile.length() > 0) {
                startUCropWithLocalFile(localFile, context, cropLauncher)
                true
            } else {
                false
            }
        }

        ContentResolver.SCHEME_CONTENT -> {
            val tempFile = copyUriToTempFile(context, imageUri)
            if (tempFile != null) {
                startUCropWithLocalFile(tempFile, context, cropLauncher)
                true
            } else {
                false
            }
        }

        else -> false
    }
}

@Composable
private fun AvatarUploadSection(
    avatarUrl: String?,
    avatarUrls: List<String> = emptyList(),
    selectedIndex: Int = 0,
    isGenerating: Boolean = false,
    isUploadingGallery: Boolean = false,
    croppedAvatarUrl: String? = null,
    agentId: String? = null,
    onGenerateClick: () -> Unit,
    onImageSelected: (Int) -> Unit = {},
    onRegenerate: (String) -> Unit = {},
    onFaceEdit: () -> Unit = {},
    onUploadFromGallery: () -> Unit = {},
    onRemoveImage: (Int) -> Unit = {},
) {
    // 首次进入页面时，显空状态检查：只有当所有头像 URL 都为空时才认为是空状态
    // 需要检查 avatarUrls、avatarUrl 和 croppedAvatarUrl
    val isEmpty = avatarUrls.isEmpty() && avatarUrl == null && croppedAvatarUrl == null
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = UiConfigs.CreateRole.VisualAppearance.SectionVerticalPadding),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier =
                Modifier.fillMaxWidth()
                    .let { modifier ->
                        if (isEmpty) {
                            modifier
                                .wrapContentHeight()
                                .background(
                                    color = UiConfigs.Colors.InputSurface,
                                    shape = RoundedCornerShape(16.dp),
                                )
                                .noRippleClickable { onGenerateClick() }
                        } else {
                            modifier
                                .wrapContentHeight()
                                .background(
                                    color = Color.Black,
                                    shape = RoundedCornerShape(16.dp),
                                )
                        }
                    },
            contentAlignment = Alignment.Center,
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .wrapContentHeight()
            ) {
            when {
                isGenerating || isUploadingGallery -> {
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
                            .fillMaxWidth()
                            .aspectRatio(UiConfigs.CreateRole.VisualAppearance.ASPECT_RATIO)
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
                // 优先显示裁剪后的头像（如果存在），因为这是最终要使用的头像
                croppedAvatarUrl != null -> {
                    LogUtils.d(
                        "AvatarUploadSection: Displaying cropped avatar with URL: $croppedAvatarUrl"
                    )

                    val previewUrl =
                        getCdnImageUrl(
                            croppedAvatarUrl,
                            width = Config.TextToImage.Preview.WIDTH,
                            quality = Config.TextToImage.Preview.QUALITY,
                        )
                    AsyncImage(
                        model = previewUrl ?: croppedAvatarUrl,
                        contentDescription = stringResource(R.string.content_desc_generated_avatar),
                        modifier = Modifier
                            .fillMaxWidth()
                            .aspectRatio(UiConfigs.CreateRole.VisualAppearance.ASPECT_RATIO)
                            .clip(RoundedCornerShape(8.dp)),
                        contentScale = ContentScale.Crop,
                        onSuccess = {
                            LogUtils.d(
                                "AvatarUploadSection: Cropped avatar image loaded successfully: $croppedAvatarUrl, preview: $previewUrl"
                            )
                        },
                        onError = {
                            LogUtils.e(
                                "AvatarUploadSection: Failed to load cropped avatar image: $croppedAvatarUrl"
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
                            .fillMaxWidth()
                            .aspectRatio(UiConfigs.CreateRole.VisualAppearance.ASPECT_RATIO)
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
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier =
                            Modifier.padding(UiConfigs.CreateRole.VisualAppearance.EmptyStateInnerPadding),
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            // Generate Avatar Button
                            Button(
                                onClick = onGenerateClick,
                                modifier = Modifier.weight(1f),
                                colors =
                                    ButtonDefaults.buttonColors(
                                        containerColor = Color(
                                            0x1A78599A
                                        )
                                    ),
                                shape = RoundedCornerShape(12.dp),
                            ) {
                                Column(
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    modifier =
                                        Modifier.padding(
                                            UiConfigs.CreateRole.VisualAppearance
                                                .EmptyStateButtonContentPadding
                                        ),
                                ) {
                                    Icon(
                                        painter = painterResource(R.drawable.instant_mix_24px),
                                        contentDescription = null,
                                        modifier = Modifier.size(32.dp),
                                        tint = Color.White,
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = stringResource(R.string.generate_avatar_title_full),
                                        fontSize = 12.sp,
                                        color = Color.White,
                                        textAlign = TextAlign.Center,
                                    )
                                }
                            }

                            // Upload from Gallery Button
                            Button(
                                onClick = onUploadFromGallery,
                                modifier = Modifier.weight(1f),
                                colors =
                                    ButtonDefaults.buttonColors(
                                        containerColor = Color(
                                            0x1A78599A
                                        )
                                    ),
                                shape = RoundedCornerShape(12.dp),
                            ) {
                                Column(
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    modifier =
                                        Modifier.padding(
                                            UiConfigs.CreateRole.VisualAppearance
                                                .EmptyStateButtonContentPadding
                                        ),
                                ) {
                                    Icon(
                                        imageVector = Icons.Outlined.Upload,
                                        contentDescription = null,
                                        modifier = Modifier.size(32.dp),
                                        tint = Color.White,
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Text(
                                        text = stringResource(R.string.upload_from_gallery),
                                        fontSize = 12.sp,
                                        color = Color.White,
                                        textAlign = TextAlign.Center,
                                    )
                                }
                            }
                        }
                    }
                }
            }

            croppedAvatarUrl?.let {
                AsyncImage(
                    model = it,
                    contentDescription = stringResource(R.string.generate_avatar),
                    contentScale = ContentScale.Crop,
                    modifier =
                        Modifier.align(Alignment.TopStart)
                            .padding(Config.AvatarCrop.Preview.PADDING.dp)
                            .border(width = 1.dp, color = Color.White, shape = CircleShape)
                            .size(Config.AvatarCrop.Preview.SIZE.dp)
                            .clip(CircleShape),
                )
            }

        // Face edit and Report buttons - show only when there's an avatar
        if (avatarUrls.isNotEmpty() || avatarUrl != null) {
            Row(
                modifier = Modifier.align(Alignment.TopEnd).padding(8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // Report button - show only when agentId is available (edit mode)
                // 这是生图的中间流程，还没有 agentID，先设置一个临时的 agentId
                val agentId = "creation_${System.currentTimeMillis()}"
                val context = LocalContext.current
                Box(
                    modifier =
                        Modifier.background(
                            color = Color.Black.copy(alpha = 0.5f),
                            shape = RoundedCornerShape(16.dp),
                        )
                            .noRippleClickable {
                                ReportActivity.launch(context, targetType = "AGENT", targetId = agentId)
                            }
                            .padding(UiConfigs.CreateRole.VisualAppearance.FaceEditPillPadding),
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Icon(
                            imageVector = Icons.Filled.Flag,
                            contentDescription = stringResource(R.string.report_button_content_description),
                            modifier = Modifier.size(16.dp),
                            tint = Color.White,
                        )
                        Text(
                            text = stringResource(R.string.str_report),
                            color = Color.White,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium,
                        )
                    }
                }

                // Crop button
                Box(
                    modifier =
                        Modifier.background(
                            color = Color.Black.copy(alpha = 0.5f),
                            shape = RoundedCornerShape(16.dp),
                        )
                            .noRippleClickable { onFaceEdit() }
                            .padding(UiConfigs.CreateRole.VisualAppearance.FaceEditPillPadding),
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
            }
        }
        Spacer(Modifier.height(8.dp))
        // 底部一行，生成的ai模型的照片图像 Floating thumbnail row at the bottom of preview
        if (avatarUrls.isNotEmpty()) {
            Row(
                modifier =
                    Modifier.fillMaxWidth()
                        .background(
                            color = Color.Black.copy(alpha = 0.5f),
                            shape = RoundedCornerShape(12.dp),
                        )
                        .padding(12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // Fixed Regen button on the left
                Box(modifier = Modifier.width(88.dp).aspectRatio(9 / 16f)) {
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
                                            Modifier.width(88.dp)
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
                                                Modifier.fillMaxSize()
                                                    .clip(RoundedCornerShape(8.dp)),
                                            contentScale = ContentScale.Crop,
                                        )

                                        Box(
                                            modifier =
                                                Modifier.align(Alignment.TopEnd)
                                                    .padding(4.dp)
                                                    .size(22.dp)
                                                    .clip(CircleShape)
                                                    .background(Color.Black.copy(alpha = 0.7f))
                                                    .noRippleClickable { onRemoveImage(index) },
                                            contentAlignment = Alignment.Center,
                                        ) {
                                            Icon(
                                                imageVector = Icons.Filled.Close,
                                                contentDescription =
                                                    stringResource(
                                                        R.string.remove_background_image
                                                    ),
                                                tint = Color.White,
                                                modifier = Modifier.size(14.dp),
                                            )
                                        }
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
    minLines: Int = 2,
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
            maxLength = maxLength,
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
        IgnoreSystemFontScaling {
            Text(
                text = text,
                fontSize = UiConfigs.CreateRole.GenderSelection.ButtonFontSize,
                color = Color.White,
                modifier = Modifier.padding(horizontal = 2.dp, vertical = 4.dp),
            )
        }
    }
}

@Composable
private fun VisibilitySwitchSection(
    isPublic: Boolean,
    onPublicChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier = modifier) {
        Text(
            text = stringResource(R.string.visibility_required_title_full),
            fontSize = 16.sp,
            color = Color.White,
            fontWeight = FontWeight.Medium,
        )
        Spacer(modifier = Modifier.height(12.dp))
        Row(
            modifier =
                Modifier.fillMaxWidth()
                    .background(color = UiConfigs.Colors.InputSurface, shape = RoundedCornerShape(12.dp))
                    .padding(horizontal = 12.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = if (isPublic) {
                    stringResource(R.string.visibility_public_full)
                } else {
                    stringResource(R.string.visibility_private_full)
                },
                color = Color.White,
                fontSize = 14.sp,
                modifier = Modifier.weight(1f),
            )
            Switch(
                checked = isPublic,
                onCheckedChange = onPublicChange,
                colors =
                    SwitchDefaults.colors(
                        checkedThumbColor = Color.White,
                        uncheckedThumbColor = Color.White,
                        checkedTrackColor = Color.Green,
                        uncheckedTrackColor = Color.White.copy(alpha = 0.25f),
                        checkedBorderColor = Color.Transparent,
                        uncheckedBorderColor = Color.Transparent,
                    ),
            )
        }
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
            Modifier.fillMaxWidth()
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
            CircularProgressIndicator(
                color = Color.White,
                modifier = Modifier.size(24.dp),
                strokeWidth = 2.5.dp,
            )
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

    object AvatarCrop {
        object Preview {
            /** 裁剪头像预览尺寸 */
            const val SIZE = 40
            const val PADDING = 8
        }
    }
}
