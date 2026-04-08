package com.ai.imate.main

import android.app.Activity
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.navigation3.rememberViewModelStoreNavEntryDecorator
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.runtime.rememberSaveableStateHolderNavEntryDecorator
import androidx.navigation3.ui.NavDisplay
import com.ai.imate.account.navigation.EmailAuthNavHost
import com.ai.imate.account.navigation.Login
import com.ai.imate.chat.Chat
import com.ai.imate.chat.ChatScreen
import com.ai.imate.main.viewmodel.MainViewModel

@Composable
fun MainScreen() {
    val context = LocalContext.current
    val viewModel = viewModel<MainViewModel>()
    val isLogin by viewModel.isLogin.collectAsState(null)

    if (isLogin != null) {
        val backStack = rememberNavBackStack( if (isLogin == true) Chat else Login)

        NavDisplay(
            backStack = backStack,
            modifier = Modifier.fillMaxSize(),
            onBack = {
                if (backStack.size > 1) {
                    backStack.removeLastOrNull()
                } else {
                    (context as? Activity)?.finish()
                }
            },
            entryDecorators = listOf(
                // Add the default decorators for managing scenes and saving state
                rememberSaveableStateHolderNavEntryDecorator(),
                // Then add the view model store decorator
                rememberViewModelStoreNavEntryDecorator()
            ),
            entryProvider = entryProvider {
                entry<Login> {
                    EmailAuthNavHost(
                        onLoginSuccess = {
                            backStack.clear()
                            backStack.add(Chat)
                        },
                        onOpenTerms = {
                        },
                        onOpenPrivacy = {
                        },
                    )
                }
                entry<Chat> {
                    ChatScreen()
                }
            }
        )
    }
}