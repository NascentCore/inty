package com.ai.inty

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewModelScope
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.InitState
import com.ai.inty.viewmodels.SplashViewModel
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.launch

/**
 * splash 启动页
 */
class SplashActivity : ComponentActivity() {

    private val viewModel: SplashViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Set status bar icons to white for dark theme
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
        windowInsetsController.isAppearanceLightStatusBars = false
        setContent {
            IntyTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { _ ->
                    Box(
                        modifier = Modifier.fillMaxSize()
                    ) {
                        Image(
                            modifier = Modifier.fillMaxSize(),
                            painter = painterResource(R.drawable.app_bg),
                            contentScale = ContentScale.Crop,
                            alignment = Alignment.TopCenter,
                            contentDescription = ""
                        )
                        Image(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .padding(bottom = 80.dp)
                                .size(80.dp)
                                .clip(RoundedCornerShape(10.dp)),
                            painter = painterResource(R.drawable.app_icon),
                            contentDescription = ""
                        )

                    }

                }
            }
        }

        viewModel.initTask()

        viewModel.viewModelScope.launch {
            viewModel.initState.collect {
                EasyLog.log("initState=$it")

                when (it) {
                    InitState.Loading -> {
                        // 正在加载中，继续显示 Splash 页面
                        EasyLog.log("Initialization in progress...")
                    }

                    InitState.Success -> {
                        TheRouter.build(Constant.ROUTE_MAIN)
                            .navigation(this@SplashActivity)
                        finish()
                    }

                    InitState.Failed -> {
                        // 初始化失败，显示错误信息并重试
                        EasyLog.log("Initialization failed, showing error")
                        // 可以在这里显示错误提示，或者自动重试
                        // 暂时直接跳转到主页面，让用户手动处理
                        TheRouter.build(Constant.ROUTE_MAIN)
                            .navigation(this@SplashActivity)
                        finish()
                    }
                }
            }
        }

    }
}