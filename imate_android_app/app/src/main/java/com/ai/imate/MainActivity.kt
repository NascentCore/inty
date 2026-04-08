package com.ai.imate

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.navigation3.rememberViewModelStoreNavEntryDecorator
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.runtime.rememberSaveableStateHolderNavEntryDecorator
import androidx.navigation3.ui.NavDisplay
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.ai.core.ui.theme.IMateTheme
import com.ai.core.utils.ToastUtils
import com.ai.imate.account.navigation.EmailAuthNavHost
import com.ai.imate.account.navigation.Login
import com.ai.imate.chat.Chat
import com.ai.imate.chat.ChatScreen
import com.ai.imate.main.MainScreen
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

                            val message = it.message
                            if (!message.isNullOrEmpty()) {
                                ToastUtils.showShort(message)
                            }
                        }
                }

                MainScreen()
            }
        }
    }
}


