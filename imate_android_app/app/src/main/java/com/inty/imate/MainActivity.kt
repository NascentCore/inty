package com.inty.imate

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.LaunchedEffect
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.ai.core.data.exceptions.IntyException
import com.ai.core.ui.theme.IMateTheme
import com.ai.core.utils.ToastUtils
import com.inty.imate.main.MainScreen
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.filterNotNull

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            IMateTheme {
                LaunchedEffect(Unit) {
                    GlobalErrorHandler.error
                        .filterNotNull()
                        .collect {
                            it.printStackTrace()

                            when (it) {
                                is IntyException -> {
                                    val message = it.msg
                                    if (message.isNotEmpty()) {
                                        ToastUtils.showShort(message)
                                    }
                                }
                                else -> {
                                    val message = it.message
                                    if (!message.isNullOrEmpty()) {
                                        ToastUtils.showShort(message)
                                    }
                                }
                            }
                        }
                }

                MainScreen()
            }
        }
    }
}


