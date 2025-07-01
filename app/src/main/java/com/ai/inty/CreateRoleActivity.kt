package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
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
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.ai.inty.beans.AgentInfo
import com.therouter.router.Autowired

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
    var visibility by remember { mutableStateOf(editAgent?.visibility ?: "PUBLIC") }
    var isLoading by remember { mutableStateOf(false) }
    var avatarUrl by remember { mutableStateOf<String?>(editAgent?.avatar?.takeIf { it.isNotBlank() }) }
    
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    
    // 检查是否有生成的头像URL - 使用DisposableEffect来监听生命周期
    DisposableEffect(Unit) {
        val checkAvatarUrl = {
            EasyLog.log("Checking for generated avatar URL...")
            val generatedUrl = AvatarManager.getAndClearGeneratedAvatarUrl()
            if (generatedUrl != null && generatedUrl.isNotBlank()) {
                avatarUrl = generatedUrl
                EasyLog.log("Retrieved generated avatar URL: $generatedUrl")
            } else {
                EasyLog.log("No generated avatar URL found")
            }
        }
        
        // 初始检查
        checkAvatarUrl()
        
        onDispose { }
    }
    
    // 监听Activity生命周期，特别是onResume事件
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                EasyLog.log("Activity resumed - checking for new avatar URL")
                val currentUrl = AvatarManager.getCurrentAvatarUrl()
                if (currentUrl != null && currentUrl != avatarUrl) {
                    EasyLog.log("Detected new avatar URL on resume: $currentUrl")
                    avatarUrl = AvatarManager.getAndClearGeneratedAvatarUrl()
                }
            }
        }
        
        lifecycleOwner.lifecycle.addObserver(observer)
        
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
        }
    }
    
    // 添加LaunchedEffect来监听activity的resume状态，以便在从AvatarGenerateActivity返回时检查
    LaunchedEffect(Unit) {
        // 定期检查是否有新的头像URL (作为备用机制)
        while (true) {
            kotlinx.coroutines.delay(1000) // 每1秒检查一次
            val currentUrl = AvatarManager.getCurrentAvatarUrl()
            if (currentUrl != null && currentUrl != avatarUrl) {
                EasyLog.log("Detected new avatar URL via polling: $currentUrl")
                avatarUrl = AvatarManager.getAndClearGeneratedAvatarUrl()
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
                        text = if (isEditMode) "Edit InTy" else "Create InTy",
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
                .padding(horizontal = 20.dp)
        ) {
            Spacer(modifier = Modifier.height(24.dp))
            
            // Avatar Upload Section
            AvatarUploadSection(
                avatarUrl = avatarUrl,
                onGenerateClick = {
                    onAvatarGenerateClick()
                    // 当点击生成头像时，不清除当前URL，让用户返回时检查新的URL
                }
            )
            
            Spacer(modifier = Modifier.height(32.dp))
            
            // Name Field
            CustomTextField(
                label = "Name *",
                value = name,
                onValueChange = { name = it },
                placeholder = "Name your InTy"
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
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // Sound Section
            SoundSelectionSection()
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // Visibility Section
            VisibilitySelectionSection(
                selectedVisibility = visibility,
                onVisibilityChange = { visibility = it }
            )
            
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
                    
                    // Log avatar URL status
                    EasyLog.log("Create button clicked - Avatar URL: $avatarUrl")
                    if (avatarUrl == null) {
                        EasyLog.log("Warning: Avatar URL is null when creating agent", EasyLog.WARN)
                        // Check if there's an avatar URL in AvatarManager that wasn't picked up
                        val currentAvatarUrl = AvatarManager.getCurrentAvatarUrl()
                        if (currentAvatarUrl != null) {
                            EasyLog.log("Found avatar URL in AvatarManager: $currentAvatarUrl")
                            avatarUrl = AvatarManager.getAndClearGeneratedAvatarUrl()
                        }
                    }
                    
                    isLoading = true
                    
                    try {
                        // Create API request
                        EasyLog.log("${if (isEditMode) "Updating" else "Creating"} agent with avatar URL: $avatarUrl")
                        val request = CreateAgentRequest(
                            name = name,
                            gender = gender,
                            avatar = avatarUrl,
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
                                    Toast.makeText(context, "角色创建成功！", Toast.LENGTH_SHORT).show()
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
    onGenerateClick: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            modifier = Modifier
                .size(120.dp)
                .border(
                    width = 2.dp,
                    color = Color(0xFFE91E63),
                    shape = RoundedCornerShape(12.dp)
                )
                .background(
                    color = Color(0x1A78599A),
                    shape = RoundedCornerShape(12.dp)
                )
                .noRippleClickable { onGenerateClick() },
            contentAlignment = Alignment.Center
        ) {
            if (avatarUrl != null) {
                EasyLog.log("AvatarUploadSection: Displaying avatar with URL: $avatarUrl")
                AsyncImage(
                    model = avatarUrl,
                    contentDescription = "Generated Avatar",
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(4.dp),
                    contentScale = ContentScale.Crop,
                    onSuccess = { 
                        EasyLog.log("AvatarUploadSection: Avatar image loaded successfully: $avatarUrl") 
                    },
                    onError = { 
                        EasyLog.log("AvatarUploadSection: Failed to load avatar image: $avatarUrl", EasyLog.ERROR) 
                    }
                )
            } else {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Image(
                        painter = painterResource(R.drawable.btn_add),
                        contentDescription = null,
                        modifier = Modifier.size(32.dp)
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Generate\nAvatar",
                        fontSize = 12.sp,
                        color = Color.White.copy(0.7f),
                        textAlign = TextAlign.Center
                    )
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
                modifier = Modifier.weight(0.8f)
            )
            GenderButton(
                text = "Non-Binary",
                isSelected = selectedGender == "NON_BINARY",
                onClick = { onGenderChange("NON_BINARY") },
                modifier = Modifier.weight(1.4f)
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
                text = if (isEditMode) "Update My InTy" else "Create My InTy",
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White
            )
        }
    }
}