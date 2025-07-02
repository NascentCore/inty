package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.clickable
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.noRippleClickable
import com.ai.inty.base.AntiClick
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.MainViewModel
import com.ai.inty.beans.CreateAgentRequest
import com.ai.inty.viewmodels.HomeTabIndex
import com.therouter.TheRouter
import com.therouter.router.Route
import androidx.lifecycle.ViewModelProvider
import androidx.compose.ui.platform.LocalContext
import android.widget.Toast
import com.inty.utils.log.EasyLog
import com.ai.inty.Constant
import com.ai.inty.utils.AvatarManager
import com.ai.inty.net.IAgentApi
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.ai.inty.R
import com.ai.inty.beans.AgentInfo
import com.therouter.router.Autowired
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.compose.rememberLauncherForActivityResult
import com.yalantis.ucrop.UCrop
import android.net.Uri
import java.io.File
import java.util.UUID
import android.graphics.Color as AndroidColor

@Route(path = Constant.ROUTE_CREATE_ROLE)
class CreateRoleActivity : BaseActivity() {

    @Autowired
    var agent: AgentInfo? = null

    private val mainViewModel: MainViewModel by lazy {
        ViewModelProvider(this)[MainViewModel::class.java]
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            IntyTheme {
                CreateRolePage(
                    modifier = Modifier.fillMaxSize(),
                    mainViewModel = mainViewModel,
                    onBack = { finish() },
                    onCreateSuccess = { finish() },
                    onAvatarGenerateClick = {
                        TheRouter.build(Constant.ROUTE_AVATAR_GENERATE)
                            .navigation(this@CreateRoleActivity)
                    },
                    editAgent = agent
                )
            }
        }
    }
    
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CreateRolePage(
    modifier: Modifier = Modifier,
    mainViewModel: MainViewModel,
    onBack: () -> Unit,
    onCreateSuccess: () -> Unit,
    onAvatarGenerateClick: () -> Unit,
    editAgent: AgentInfo? = null
) {
    val isEditMode = editAgent != null
    
    var name by remember { mutableStateOf(editAgent?.name ?: "") }
    var gender by remember { mutableStateOf(editAgent?.gender ?: "FEMALE") }
    var settings by remember { mutableStateOf(editAgent?.settings?.get("description") as? String ?: editAgent?.prompt ?: "") }
    var intro by remember { mutableStateOf(editAgent?.intro ?: "") }
    var opening by remember { mutableStateOf(editAgent?.opening ?: "") }
    var visibility by remember { mutableStateOf(editAgent?.visibility ?: "PRIVATE") }
    var isLoading by remember { mutableStateOf(false) }
    // Initialize image states based on edit mode
    var avatarUrl by remember { 
        mutableStateOf<String?>(
            if (isEditMode) editAgent?.background?.takeIf { it.isNotBlank() } else null
        ) 
    }
    var avatarUrls by remember { 
        mutableStateOf<List<String>>(
            if (isEditMode) editAgent?.backgroundImages ?: emptyList() else emptyList()
        ) 
    }
    var selectedImageIndex by remember { 
        mutableStateOf(
            if (isEditMode && editAgent?.backgroundImages?.isNotEmpty() == true) {
                // Find the index of the background image in the background_images list
                editAgent.backgroundImages.indexOf(editAgent.background).takeIf { it >= 0 } ?: 0
            } else {
                0
            }
        ) 
    }
    var isGeneratingAvatar by remember { mutableStateOf(false) }
    var croppedAvatarUrl by remember { 
        mutableStateOf<String?>(
            if (isEditMode) editAgent?.avatar?.takeIf { it.isNotBlank() && it != editAgent?.background } else null
        ) 
    }
    
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    
    // Clear avatar data when creating new character
    LaunchedEffect(isEditMode) {
        if (!isEditMode) {
            AvatarManager.clearAllAvatarData()
            EasyLog.log("Cleared avatar data for new character creation")
        }
    }
    
    // UCrop launcher for avatar cropping
    val cropLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == android.app.Activity.RESULT_OK) {
            result.data?.let { data ->
                val resultUri = UCrop.getOutput(data)
                if (resultUri != null) {
                    EasyLog.log("Avatar cropped successfully: $resultUri")
                    
                    // Upload the cropped image to server
                    try {
                        val file = File(resultUri.path!!)
                        val requestFile = file.asRequestBody("image/*".toMediaTypeOrNull())
                        val body = MultipartBody.Part.createFormData("file", file.name, requestFile)
                        
                        val agentApi = TheRouter.get(IAgentApi::class.java)
                        
                        // Use the mainViewModel's scope to launch the coroutine
                        mainViewModel.viewModelScope.launch(Dispatchers.IO) {
                            try {
                                val response = agentApi!!.uploadAvatar(body)
                                when (response) {
                                    is com.architecture.httplib.core.HttpResult.Success -> {
                                        val uploadedUrl = response.data.url
                                        EasyLog.log("Avatar uploaded successfully: $uploadedUrl")
                                        
                                        // Update UI on main thread
                                        kotlinx.coroutines.withContext(Dispatchers.Main) {
                                            croppedAvatarUrl = uploadedUrl
                                            Toast.makeText(context, "Avatar cropped and uploaded", Toast.LENGTH_SHORT).show()
                                        }
                                    }
                                    is com.architecture.httplib.core.HttpResult.Failure -> {
                                        EasyLog.log("Upload failed: ${response.message}", EasyLog.ERROR)
                                        kotlinx.coroutines.withContext(Dispatchers.Main) {
                                            Toast.makeText(context, "Upload failed: ${response.message}", Toast.LENGTH_LONG).show()
                                        }
                                    }
                                }
                            } catch (e: Exception) {
                                EasyLog.log("Upload exception: ${e.message}", EasyLog.ERROR)
                                kotlinx.coroutines.withContext(Dispatchers.Main) {
                                    Toast.makeText(context, "Upload failed: ${e.message}", Toast.LENGTH_LONG).show()
                                }
                            }
                        }
                    } catch (e: Exception) {
                        EasyLog.log("Failed to prepare upload: ${e.message}", EasyLog.ERROR)
                        Toast.makeText(context, "Failed to prepare upload: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        } else if (result.resultCode == UCrop.RESULT_ERROR) {
            result.data?.let { data ->
                val cropError = UCrop.getError(data)
                EasyLog.log("UCrop error: ${cropError?.message}", EasyLog.ERROR)
                Toast.makeText(context, "Crop failed: ${cropError?.message}", Toast.LENGTH_LONG).show()
            }
        }
    }
    
    // 检查是否有生成的头像URL - 使用DisposableEffect来监听生命周期
    DisposableEffect(Unit) {
        val checkAvatarStatus = {
            EasyLog.log("Initial avatar generation status check...")
            
            // Check if generation is in progress
            val generatingStatus = AvatarManager.isGenerating()
            isGeneratingAvatar = generatingStatus
            EasyLog.log("Generation status: $generatingStatus")
            
            // Check for multiple generated URLs
            val currentUrls = AvatarManager.getCurrentAvatarUrls()
            if (currentUrls.isNotEmpty()) {
                avatarUrls = currentUrls
                selectedImageIndex = AvatarManager.getSelectedImageIndex()
                avatarUrl = null // Clear single URL when we have multiple
                EasyLog.log("Retrieved generated avatar URLs: $currentUrls")
            } else {
                // Check for single generated URL
                val generatedUrl = AvatarManager.getCurrentAvatarUrl()
                if (generatedUrl != null && generatedUrl.isNotBlank()) {
                    avatarUrl = generatedUrl
                    avatarUrls = emptyList()
                    EasyLog.log("Retrieved generated avatar URL: $generatedUrl")
                }
            }
            
            // Check for generation errors
            val error = AvatarManager.getGenerationError()
            if (error != null) {
                EasyLog.log("Generation error found: $error")
                Toast.makeText(context, error, Toast.LENGTH_LONG).show()
                isGeneratingAvatar = false
            }
            
            // Show current generation prompt if generating
            if (generatingStatus) {
                val prompt = AvatarManager.getGenerationPrompt()
                EasyLog.log("Currently generating with prompt: '$prompt'")
            }
        }
        
        // 初始检查
        checkAvatarStatus()
        
        onDispose { }
    }
    
    // 监听Activity生命周期，特别是onResume事件
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                EasyLog.log("Activity resumed - checking for new avatar status")
                
                // Check generation status
                isGeneratingAvatar = AvatarManager.isGenerating()
                
                // Check for multiple URLs
                val currentUrls = AvatarManager.getCurrentAvatarUrls()
                if (currentUrls.isNotEmpty() && currentUrls != avatarUrls) {
                    EasyLog.log("Detected new avatar URLs on resume: $currentUrls")
                    avatarUrls = currentUrls
                    selectedImageIndex = AvatarManager.getSelectedImageIndex()
                    avatarUrl = null
                } else {
                    // Check for single URL
                    val currentUrl = AvatarManager.getCurrentAvatarUrl()
                    if (currentUrl != null && currentUrl != avatarUrl) {
                        EasyLog.log("Detected new avatar URL on resume: $currentUrl")
                        avatarUrl = currentUrl
                        avatarUrls = emptyList()
                    }
                }
                
                // Check for errors
                val error = AvatarManager.getGenerationError()
                if (error != null) {
                    Toast.makeText(context, error, Toast.LENGTH_LONG).show()
                    isGeneratingAvatar = false
                }
            }
        }
        
        lifecycleOwner.lifecycle.addObserver(observer)
        
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }
    
    // 添加LaunchedEffect来监听avatar生成状态
    LaunchedEffect(Unit) {
        // 定期检查生成状态 (作为备用机制)
        while (true) {
            kotlinx.coroutines.delay(2000) // 每2秒检查一次
            
            val currentGenerationStatus = AvatarManager.isGenerating()
            if (currentGenerationStatus != isGeneratingAvatar) {
                EasyLog.log("Generation status changed: $isGeneratingAvatar -> $currentGenerationStatus")
                isGeneratingAvatar = currentGenerationStatus
            }
            
            // 只在状态发生变化时记录，减少日志噪音
            val currentUrls = AvatarManager.getCurrentAvatarUrls()
            if (currentUrls.isNotEmpty() && currentUrls != avatarUrls) {
                EasyLog.log("Detected new avatar URLs via polling: $currentUrls")
                avatarUrls = currentUrls
                selectedImageIndex = AvatarManager.getSelectedImageIndex()
                avatarUrl = null
                EasyLog.log("Updated UI with ${currentUrls.size} generated avatars")
            } else {
                val currentUrl = AvatarManager.getCurrentAvatarUrl()
                if (currentUrl != null && currentUrl != avatarUrl) {
                    EasyLog.log("Detected new avatar URL via polling: $currentUrl")
                    avatarUrl = currentUrl
                    avatarUrls = emptyList()
                }
            }
            
            val error = AvatarManager.getGenerationError()
            if (error != null) {
                EasyLog.log("Generation error detected via polling: $error")
                Toast.makeText(context, error, Toast.LENGTH_LONG).show()
                isGeneratingAvatar = false
            }
            
            // 每10秒输出一次当前状态（减少日志频率）
            if (System.currentTimeMillis() % 10000 < 2000) {
                EasyLog.log("Polling status - Generating: $isGeneratingAvatar, URLs: ${avatarUrls.size}, Single URL: ${avatarUrl != null}")
            }
        }
    }
    
    // 监听avatarUrl变化
    LaunchedEffect(avatarUrl) {
        EasyLog.log("Avatar URL updated: $avatarUrl")
    }

    Scaffold(
        modifier = modifier.background(BackGround),
        containerColor = BackGround,
        topBar = {
            CenterAlignedTopAppBar(
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors().copy(containerColor = Color.Transparent),
                title = {
                    Text(
                        text = if (isEditMode) "Edit HeartMate" else "Create HeartMate",
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
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally
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
                    val sourceUri = if (avatarUrls.isNotEmpty()) {
                        Uri.parse(avatarUrls.getOrNull(selectedImageIndex) ?: avatarUrls.first())
                    } else {
                        avatarUrl?.let { Uri.parse(it) }
                    }
                    
                    if (sourceUri != null) {
                        try {
                            // Create destination file for cropped image
                            val destinationFile = File(context.cacheDir, "cropped_avatar_${UUID.randomUUID()}.jpg")
                            val destinationUri = Uri.fromFile(destinationFile)
                            
                            // Configure UCrop
                            val cropIntent = UCrop.of(sourceUri, destinationUri)
                                .withAspectRatio(1f, 1f) // Square aspect ratio for avatar
                                .withMaxResultSize(512, 512) // Reasonable size for avatars
                                .withOptions(UCrop.Options().apply {
                                    setCompressionQuality(90)
                                    setHideBottomControls(false)
                                    setFreeStyleCropEnabled(false)
                                    setToolbarTitle("Crop Avatar")
                                    setStatusBarColor(AndroidColor.parseColor("#1C1523"))
                                    setToolbarColor(AndroidColor.parseColor("#1C1523"))
                                    setActiveControlsWidgetColor(AndroidColor.parseColor("#E91E63"))
                                    setToolbarWidgetColor(AndroidColor.WHITE)
                                    setCropFrameColor(AndroidColor.WHITE)
                                    setCropGridColor(AndroidColor.WHITE)
                                    setCircleDimmedLayer(true) // Enable circular cropping
                                    setShowCropFrame(false) // Hide square frame for circular crop
                                    setShowCropGrid(false) // Hide grid for cleaner circular crop
                                })
                                .getIntent(context)
                            
                            EasyLog.log("Starting UCrop with source: $sourceUri")
                            cropLauncher.launch(cropIntent)
                        } catch (e: Exception) {
                            EasyLog.log("Failed to start UCrop: ${e.message}", EasyLog.ERROR)
                            Toast.makeText(context, "Failed to open crop editor", Toast.LENGTH_SHORT).show()
                        }
                    } else {
                        Toast.makeText(context, "No avatar image to crop", Toast.LENGTH_SHORT).show()
                    }
                }
            )
            
            Spacer(modifier = Modifier.height(32.dp))
            
            // Name Field
            CustomTextField(
                label = "Name *",
                value = name,
                onValueChange = { name = it },
                placeholder = "Name your HeartMate"
            )
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // Gender Selection
            GenderSelectionSection(
                selectedGender = gender,
                onGenderChange = { gender = it }
            )
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // Settings Field
            CustomTextField(
                label = "Settings (Determines dialogue effect) *",
                value = settings,
                onValueChange = { settings = it },
                placeholder = "Please fill in the dialogue effect...",
                minLines = 4
            )
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // Intro Field
            CustomTextField(
                label = "Intro (No impact on dialogue effect) *",
                value = intro,
                onValueChange = { intro = it },
                placeholder = "Please fill in the character introduction...",
                minLines = 3
            )
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // Opening Field
            CustomTextField(
                label = "Opening *",
                value = opening,
                onValueChange = { opening = it },
                placeholder = "Please fill in the character's opening remarks...",
                minLines = 3
            )
            
            // Spacer(modifier = Modifier.height(24.dp))
            
            // Sound Section
            // SoundSelectionSection()
            
            // Spacer(modifier = Modifier.height(24.dp))
            
            // Visibility Section
            // VisibilitySelectionSection(
            //     selectedVisibility = visibility,
            //     onVisibilityChange = { visibility = it }
            // )
            
            Spacer(modifier = Modifier.height(40.dp))
            
            // Create Button
            CreateButton(
                isLoading = isLoading,
                isEditMode = isEditMode,
                onClick = {
                    // Validate required fields
                    if (name.isBlank() || intro.isBlank() || opening.isBlank() || settings.isBlank()) {
                        Toast.makeText(context, "请填写所有必填字段", Toast.LENGTH_SHORT).show()
                        return@CreateButton
                    }
                    
                    // Prepare avatar and background fields according to new logic
                    val backgroundUrl = if (avatarUrls.isNotEmpty()) {
                        // Use selected image from generated grid as background
                        avatarUrls.getOrNull(selectedImageIndex) ?: avatarUrls.first()
                    } else {
                        // Use single generated image as background
                        avatarUrl
                    }
                    
                    // Determine final avatar URL - if no cropped avatar, use background as avatar
                    val finalAvatarUrl = croppedAvatarUrl ?: backgroundUrl
                    val backgroundImagesList = if (avatarUrls.isNotEmpty()) avatarUrls else listOfNotNull(avatarUrl)
                    
                    EasyLog.log("Create button clicked - Final Avatar URL: $finalAvatarUrl")
                    EasyLog.log("Create button clicked - Background URL: $backgroundUrl")
                    EasyLog.log("Create button clicked - Background Images List: $backgroundImagesList")
                    EasyLog.log("Create button clicked - Cropped Avatar URL: $croppedAvatarUrl")
                    EasyLog.log("Create button clicked - Avatar equals background: ${finalAvatarUrl == backgroundUrl}")
                    
                    // Save background for chat usage
                    if (backgroundUrl != null) {
                        AvatarManager.setChatBackgroundUrl(backgroundUrl)
                    }
                    
                    isLoading = true
                    
                    try {
                        // Create API request
                        EasyLog.log("${if (isEditMode) "Updating" else "Creating"} agent with avatar URL: $finalAvatarUrl")
                        val request = CreateAgentRequest(
                            name = name,
                            gender = gender,
                            avatar = finalAvatarUrl,
                            background = backgroundUrl,
                            backgroundImages = backgroundImagesList,
                            settings = mapOf("description" to settings),
                            intro = intro,
                            opening = opening,
                            visibility = visibility,
                            prompt = settings
                        )
                        EasyLog.log("${if (isEditMode) "Update" else "Create"} agent request: $request")
                        EasyLog.log("${if (isEditMode) "Update" else "Create"} agent request avatar field: ${request.avatar}")
                        
                        // Call API through ViewModel
                        if (isEditMode && editAgent != null) {
                            mainViewModel.updateAgent(
                                agentId = editAgent.id,
                                request = request,
                                onSuccess = { agentInfo ->
                                    isLoading = false
                                    Toast.makeText(context, "角色更新成功！", Toast.LENGTH_SHORT).show()
                                    onCreateSuccess()
                                },
                                onError = { error ->
                                    isLoading = false
                                    val errorMessage = if (error.isBlank()) "更新失败，请稍后重试" else "更新失败：$error"
                                    Toast.makeText(context, errorMessage, Toast.LENGTH_LONG).show()
                                }
                            )
                        } else {
                            mainViewModel.createAgent(
                                request = request,
                                onSuccess = { agentInfo ->
                                    isLoading = false
                                    Toast.makeText(context, context.getString(R.string.create_ai_successfully), Toast.LENGTH_SHORT).show()
                                    onCreateSuccess()
                                },
                                onError = { error ->
                                    isLoading = false
                                    val errorMessage = if (error.isBlank()) "创建失败，请稍后重试" else "创建失败：$error"
                                    Toast.makeText(context, errorMessage, Toast.LENGTH_LONG).show()
                                }
                            )
                        }
                    } catch (e: Exception) {
                        isLoading = false
                        val errorMessage = "${if (isEditMode) "更新" else "创建"}出错：${e.message ?: "未知错误"}"
                        Toast.makeText(context, errorMessage, Toast.LENGTH_LONG).show()
                        EasyLog.log("${if (isEditMode) "UpdateRole" else "CreateRole"} error: ${e.message}", EasyLog.ERROR)
                        EasyLog.log(e)
                    }
                }
            )
            
            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}

@Composable
fun AvatarUploadSection(
    avatarUrl: String?,
    avatarUrls: List<String> = emptyList(),
    selectedIndex: Int = 0,
    isGenerating: Boolean = false,
    croppedAvatarUrl: String? = null,
    onGenerateClick: () -> Unit,
    onImageSelected: (Int) -> Unit = {},
    onRegenerate: (String) -> Unit = {},
    onFaceEdit: () -> Unit = {}
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(320.dp)
                .let { modifier ->
                    if (avatarUrls.isEmpty() && avatarUrl == null) {
                        modifier
                            .background(
                                color = Color(0x1A78599A),
                                shape = RoundedCornerShape(16.dp)
                            )
                            .border(
                                width = 4.dp,
                                color = Color(0xFFE91E63),
                                shape = RoundedCornerShape(16.dp)
                            )
                            .noRippleClickable { onGenerateClick() }
                    } else {
                        modifier
                            .background(
                                color = Color.Black,
                                shape = RoundedCornerShape(16.dp)
                            )
                    }
                },
            contentAlignment = Alignment.Center
        ) {
            when {
                isGenerating -> {
                    com.ai.inty.ThreeDotLoadingAnimation()
                }
                avatarUrls.isNotEmpty() -> {
                    val displayUrl = avatarUrls.getOrNull(selectedIndex) ?: avatarUrls.first()
                    EasyLog.log("AvatarUploadSection: Displaying selected avatar with URL: $displayUrl")
                    AsyncImage(
                        model = displayUrl,
                        contentDescription = "Selected Avatar",
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop,
                        onSuccess = { 
                            EasyLog.log("AvatarUploadSection: Selected avatar image loaded successfully: $displayUrl") 
                        },
                        onError = { 
                            EasyLog.log("AvatarUploadSection: Failed to load selected avatar image: $displayUrl", EasyLog.ERROR) 
                        }
                    )
                }
                avatarUrl != null -> {
                    EasyLog.log("AvatarUploadSection: Displaying avatar with URL: $avatarUrl")
                    AsyncImage(
                        model = avatarUrl,
                        contentDescription = "Generated Avatar",
                        modifier = Modifier.fillMaxSize(),
                        contentScale = ContentScale.Crop,
                        onSuccess = { 
                            EasyLog.log("AvatarUploadSection: Avatar image loaded successfully: $avatarUrl") 
                        },
                        onError = { 
                            EasyLog.log("AvatarUploadSection: Failed to load avatar image: $avatarUrl", EasyLog.ERROR) 
                        }
                    )
                }
                else -> {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Image(
                            painter = painterResource(R.drawable.btn_add),
                            contentDescription = null,
                            modifier = Modifier.size(48.dp)
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "Generate\nAvatar",
                            fontSize = 14.sp,
                            color = Color.White.copy(0.7f),
                            textAlign = TextAlign.Center
                        )
                    }
                }
            }
            
            // Face edit button - show only when there's an avatar
            if (avatarUrls.isNotEmpty() || avatarUrl != null) {
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(8.dp)
                        .background(
                            color = Color.Black.copy(alpha = 0.5f),
                            shape = RoundedCornerShape(16.dp)
                        )
                        .noRippleClickable { onFaceEdit() }
                        .padding(horizontal = 12.dp, vertical = 6.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Image(
                            painter = painterResource(R.drawable.ic_crop),
                            contentDescription = "Face edit",
                            modifier = Modifier.size(16.dp)
                        )
                        Text(
                            text = "Face edit",
                            color = Color.White,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
        }
        
        // Show cropped avatar indicator
        if (croppedAvatarUrl != null) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "✓ Cropped avatar saved",
                fontSize = 12.sp,
                color = Color(0xFF4CAF50),
                fontWeight = FontWeight.Medium
            )
        }
        
        // Show grid of multiple avatars below the main preview
        if (avatarUrls.isNotEmpty()) {
            Spacer(modifier = Modifier.height(16.dp))
            
            // Row containing Regen button on left and image grid on right
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Regen button on the left - same weight as one thumbnail
                Box(modifier = Modifier.weight(1f)) {
                    com.ai.inty.RegenButton(
                        onClick = { onRegenerate(AvatarManager.getGenerationPrompt()) },
                        enabled = !isGenerating
                    )
                }
                
                // 4张图片的网格布局 on the right
                avatarUrls.take(4).forEachIndexed { index, imageUrl ->
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .aspectRatio(1f)
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
                            contentDescription = "Generated Avatar $index",
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
}

@Composable
fun GenderSelectionSection(
    selectedGender: String,
    onGenderChange: (String) -> Unit
) {
    Column {
        Text(
            text = "Gender (Unmodified after Creation) *",
            fontSize = 16.sp,
            color = Color.White,
            fontWeight = FontWeight.Medium
        )
        Spacer(modifier = Modifier.height(12.dp))
        
        Row(
            horizontalArrangement = Arrangement.spacedBy(4.dp),
            modifier = Modifier.fillMaxWidth()
        ) {
            GenderButton(
                text = "Male",
                isSelected = selectedGender == "MALE",
                onClick = { onGenderChange("MALE") },
                modifier = Modifier.weight(0.8f)
            )
            GenderButton(
                text = "Female",
                isSelected = selectedGender == "FEMALE",
                onClick = { onGenderChange("FEMALE") },
                modifier = Modifier.weight(0.9f)
            )
            GenderButton(
                text = "Non-Binary",
                isSelected = selectedGender == "NON_BINARY",
                onClick = { onGenderChange("NON_BINARY") },
                modifier = Modifier.weight(1.1f)
            )
        }
    }
}

@Composable
fun SoundSelectionSection() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .background(
                color = Color(0x1A78599A),
                shape = RoundedCornerShape(12.dp)
            )
            .border(
                width = 1.dp,
                color = Color.White.copy(0.2f),
                shape = RoundedCornerShape(12.dp)
            )
            .padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .background(
                    color = Color(0xFFE91E63),
                    shape = RoundedCornerShape(8.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "🎵",
                fontSize = 16.sp
            )
        }
        
        Spacer(modifier = Modifier.width(12.dp))
        
        Text(
            text = "Sound *",
            fontSize = 16.sp,
            color = Color.White,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.weight(1f)
        )
        
        Text(
            text = "Inty Voice",
            fontSize = 14.sp,
            color = Color.White.copy(0.7f)
        )
        
        Spacer(modifier = Modifier.width(8.dp))
        
        Text(
            text = ">",
            fontSize = 16.sp,
            color = Color.White.copy(0.7f)
        )
    }
}

@Composable
fun VisibilitySelectionSection(
    selectedVisibility: String,
    onVisibilityChange: (String) -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .background(
                color = Color(0x1A78599A),
                shape = RoundedCornerShape(12.dp)
            )
            .border(
                width = 1.dp,
                color = Color.White.copy(0.2f),
                shape = RoundedCornerShape(12.dp)
            )
            .padding(horizontal = 16.dp)
            .noRippleClickable {
                onVisibilityChange(if (selectedVisibility == "PUBLIC") "PRIVATE" else "PUBLIC")
            },
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(32.dp)
                .background(
                    color = Color(0xFF2196F3),
                    shape = RoundedCornerShape(8.dp)
                ),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "★",
                fontSize = 16.sp,
                color = Color.White
            )
        }
        
        Spacer(modifier = Modifier.width(12.dp))
        
        Text(
            text = "Visibility *",
            fontSize = 16.sp,
            color = Color.White,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.weight(1f)
        )
        
        Text(
            text = selectedVisibility.lowercase().replaceFirstChar { it.uppercase() },
            fontSize = 14.sp,
            color = Color.White.copy(0.7f)
        )
        
        Spacer(modifier = Modifier.width(8.dp))
        
        Text(
            text = ">",
            fontSize = 16.sp,
            color = Color.White.copy(0.7f)
        )
    }
}


@Composable
fun CustomTextField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    placeholder: String,
    minLines: Int = 1
) {
    Column {
        Text(
            text = label,
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
                .let { if (minLines > 1) it.height((minLines * 24 + 32).dp) else it },
            textStyle = TextStyle(
                color = Color.White,
                fontSize = 16.sp
            ),
            cursorBrush = SolidColor(Color.White),
            decorationBox = { innerTextField ->
                Box {
                    if (value.isEmpty()) {
                        Text(
                            text = placeholder,
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
fun GenderButton(
    text: String,
    isSelected: Boolean,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
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
        colors = ButtonDefaults.buttonColors(
            containerColor = Color(0x1A78599A)
        ),
        shape = RoundedCornerShape(20.dp),
        modifier = modifier
            .border(
                width = if (isSelected) 2.dp else 1.dp,
                color = if (isSelected) Color(0xFFE91E63) else Color.White.copy(0.3f),
                shape = RoundedCornerShape(20.dp)
            )
    ) {
        Text(
            text = text,
            fontSize = 12.sp,
            color = Color.White,
            modifier = Modifier.padding(horizontal = 2.dp, vertical = 4.dp)
        )
    }
}


@Composable
fun CreateButton(
    isLoading: Boolean,
    isEditMode: Boolean = false,
    onClick: () -> Unit
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
        enabled = !isLoading,
        colors = ButtonDefaults.buttonColors(
            containerColor = Color.Transparent
        ),
        shape = RoundedCornerShape(25.dp),
        modifier = Modifier
            .fillMaxWidth()
            .height(56.dp)
            .background(
                brush = androidx.compose.ui.graphics.Brush.horizontalGradient(
                    colors = listOf(
                        Color(0xFFE91E63),
                        Color(0xFFFF9800)
                    )
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
                text = if (isEditMode) "Update My HeartMate" else "Create My HeartMate",
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White
            )
        }
    }
}

