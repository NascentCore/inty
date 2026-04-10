package com.ai.imate.main

import android.app.Activity
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.navigation3.rememberViewModelStoreNavEntryDecorator
import androidx.navigation3.runtime.NavKey
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.runtime.rememberSaveableStateHolderNavEntryDecorator
import androidx.navigation3.ui.NavDisplay
import com.ai.imate.account.navigation.EmailAuthNavHost
import com.ai.imate.account.navigation.Login
import com.ai.imate.chat.Chat
import com.ai.imate.chat.ChatScreen
import com.ai.imate.chat.InitChat
import com.ai.imate.chat.InitChatRoute
import com.ai.imate.R
import com.ai.imate.main.viewmodel.MainViewModel

@Composable
fun MainScreen() {
    val context = LocalContext.current
    val uriHandler = LocalUriHandler.current
    val viewModel = viewModel<MainViewModel>()
    val destination by viewModel.navigationDestination.collectAsState()

    val dest: NavKey? = destination
    if (dest == null) {
        Box(
            modifier =
                Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.background),
        )
        return
    }

    key(dest) {
        val backStack = rememberNavBackStack(dest)

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
                rememberSaveableStateHolderNavEntryDecorator(),
                rememberViewModelStoreNavEntryDecorator(),
            ),
            entryProvider = entryProvider {
                entry<Login> {
                    EmailAuthNavHost(
                        onLoginSuccess = {
                            viewModel.onEmailAuthLoadingFinished()
                        },
                        onOpenTerms = {
                            uriHandler.openUri(context.getString(R.string.login_terms_url))
                        },
                        onOpenPrivacy = {
                            uriHandler.openUri(context.getString(R.string.login_privacy_url))
                        },
                    )
                }
                entry<InitChat> {
                    InitChatRoute()
                }
                entry<Chat> {
                    ChatScreen()
                }
            },
        )
    }
}