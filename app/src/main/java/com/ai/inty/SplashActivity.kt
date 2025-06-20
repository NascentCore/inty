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
import androidx.compose.material3.Scaffold
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewModelScope
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.SplashViewModel
import com.inty.utils.log.EasyLog
import com.therouter.TheRouter
import kotlinx.coroutines.launch

class SplashActivity : ComponentActivity() {

    private val viewModel: SplashViewModel by viewModels();

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        enableEdgeToEdge()
        setContent {
            IntyTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
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
                            ,
                            painter = painterResource(R.drawable.app_2),
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
                    SplashViewModel.InitState.Success -> {
                        TheRouter.build(Constant.ROUTE_MAIN)
                            .navigation(this@SplashActivity)
                        finish()
                    }
                    else -> {

                    }
                }
            }
        }

    }
}