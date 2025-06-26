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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.noRippleClickable
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.MainViewModel
import com.therouter.TheRouter
import com.therouter.router.Route
import androidx.lifecycle.ViewModelProvider
import android.widget.Toast
import com.inty.utils.log.EasyLog
import com.ai.inty.beans.GenerateBackgroundRequest
import com.ai.inty.Constant
import com.ai.inty.utils.AvatarManager

@Route(path = Constant.ROUTE_AVATAR_GENERATE)
class AvatarGenerateActivity : BaseActivity() {

    private val mainViewModel: MainViewModel by lazy {
        ViewModelProvider(this)[MainViewModel::class.java]
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            IntyTheme {
                AvatarGeneratePage(
                    modifier = Modifier.fillMaxSize(),
                    mainViewModel = mainViewModel,
                    onBack = { finish() },
                    onGenerateSuccess = { imageUrl ->
                        // Store the generated image URL in AvatarManager
                        EasyLog.log("AvatarGenerateActivity: onGenerateSuccess called with URL: $imageUrl")
                        AvatarManager.setGeneratedAvatarUrl(imageUrl)
                        EasyLog.log("AvatarGenerateActivity: Avatar URL stored, finishing activity")
                        finish()
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AvatarGeneratePage(
    modifier: Modifier = Modifier,
    mainViewModel: MainViewModel,
    onBack: () -> Unit,
    onGenerateSuccess: (String) -> Unit
) {
    var prompt by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    var generatedImageUrl by remember { mutableStateOf<String?>(null) }
    
    val context = LocalContext.current

    Scaffold(
        modifier = modifier.background(BackGround),
        containerColor = BackGround,
        topBar = {
            CenterAlignedTopAppBar(
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors().copy(containerColor = Color.Transparent),
                title = {
                    Text(
                        text = "Generate Avatar",
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
            
            // Image Preview Section
            AvatarPreviewSection(
                imageUrl = generatedImageUrl,
                isLoading = isLoading
            )
            
            Spacer(modifier = Modifier.height(32.dp))
            
            // Prompt Input Field
            PromptInputField(
                value = prompt,
                onValueChange = { prompt = it }
            )
            
            Spacer(modifier = Modifier.height(32.dp))
            
            // Generate Button
            GenerateButton(
                isLoading = isLoading,
                enabled = prompt.isNotBlank(),
                onClick = {
                    if (prompt.isBlank()) {
                        Toast.makeText(context, "Please enter a prompt", Toast.LENGTH_SHORT).show()
                        return@GenerateButton
                    }
                    
                    isLoading = true
                    
                    try {
                        val request = GenerateBackgroundRequest(prompt = prompt)
                        
                        mainViewModel.generateBackground(
                            request = request,
                            onSuccess = { response ->
                                isLoading = false
                                EasyLog.log("Generated image URL: ${response.imageUrl}")
                                if (response.imageUrl.isNotBlank()) {
                                    generatedImageUrl = response.imageUrl
                                    EasyLog.log("Setting generatedImageUrl to: $generatedImageUrl")
                                    Toast.makeText(context, "Avatar generated successfully!", Toast.LENGTH_SHORT).show()
                                } else {
                                    EasyLog.log("Empty image URL received from server", EasyLog.ERROR)
                                    Toast.makeText(context, "Generated image URL is empty", Toast.LENGTH_SHORT).show()
                                }
                            },
                            onError = { error ->
                                isLoading = false
                                val errorMessage = if (error.isBlank()) "Generation failed, please try again later" else "Generation failed: $error"
                                Toast.makeText(context, errorMessage, Toast.LENGTH_LONG).show()
                            }
                        )
                    } catch (e: Exception) {
                        isLoading = false
                        val errorMessage = "Generation error: ${e.message ?: "Unknown error"}"
                        Toast.makeText(context, errorMessage, Toast.LENGTH_LONG).show()
                        EasyLog.log("Generate avatar error: ${e.message}", EasyLog.ERROR)
                        EasyLog.log(e)
                    }
                }
            )
            
            Spacer(modifier = Modifier.height(24.dp))
            
            // Use Generated Avatar Button
            if (generatedImageUrl != null) {
                UseAvatarButton(
                    onClick = {
                        onGenerateSuccess(generatedImageUrl!!)
                    }
                )
            }
            
            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}

@Composable
fun AvatarPreviewSection(
    imageUrl: String?,
    isLoading: Boolean
) {
    Box(
        modifier = Modifier
            .size(200.dp)
            .border(
                width = 2.dp,
                color = Color(0xFFE91E63),
                shape = RoundedCornerShape(16.dp)
            )
            .background(
                color = Color(0x1A78599A),
                shape = RoundedCornerShape(16.dp)
            ),
        contentAlignment = Alignment.Center
    ) {
        when {
            isLoading -> {
                CircularProgressIndicator(
                    color = Color(0xFFE91E63),
                    modifier = Modifier.size(48.dp)
                )
            }
            imageUrl != null -> {
                EasyLog.log("Displaying image with URL: $imageUrl")
                AsyncImage(
                    model = imageUrl,
                    contentDescription = "Generated Avatar",
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
                        painter = painterResource(R.drawable.btn_add),
                        contentDescription = null,
                        modifier = Modifier.size(48.dp)
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Preview\nGenerated Avatar",
                        fontSize = 14.sp,
                        color = Color.White.copy(0.7f),
                        textAlign = TextAlign.Center
                    )
                }
            }
        }
    }
}

@Composable
fun PromptInputField(
    value: String,
    onValueChange: (String) -> Unit
) {
    Column {
        Text(
            text = "Describe your desired avatar *",
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
                            text = "e.g.: A cute anime girl with long hair, big eyes, wearing a white dress...",
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
fun GenerateButton(
    isLoading: Boolean,
    enabled: Boolean,
    onClick: () -> Unit
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
                text = "Generate Avatar",
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White
            )
        }
    }
}

@Composable
fun UseAvatarButton(
    onClick: () -> Unit
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
            text = "Use This Avatar",
            fontSize = 16.sp,
            fontWeight = FontWeight.Medium,
            color = Color.White
        )
    }
}