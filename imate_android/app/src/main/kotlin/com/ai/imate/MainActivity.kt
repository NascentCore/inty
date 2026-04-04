package com.ai.imate

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.ai.imate.auth.AuthManager
import com.ai.imate.auth.AuthViewModel
import com.ai.imate.auth.DataStoreSessionStore
import com.ai.imate.auth.GoogleCredentialClient
import com.ai.imate.auth.LogcatAnalyticsLogger
import com.ai.imate.auth.RetrofitAuthRepository
import com.ai.imate.chat.ChatViewModel
import com.ai.imate.chat.InMemoryChatRepository
import com.ai.imate.ui.IMateApp

class MainActivity : ComponentActivity() {
    private val sessionStore by lazy { DataStoreSessionStore(applicationContext) }
    private val authManager by lazy {
        AuthManager(
            authRepository = RetrofitAuthRepository.fromBaseUrl(BuildConfig.API_BASE_URL),
            sessionStore = sessionStore,
            analyticsLogger = LogcatAnalyticsLogger(),
        )
    }
    private val authViewModel: AuthViewModel by viewModels {
        AuthViewModel.factory(authManager = authManager, sessionStore = sessionStore)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            Surface(color = MaterialTheme.colorScheme.background) {
                val chatViewModel: ChatViewModel = viewModel(factory = ChatViewModel.factory(InMemoryChatRepository()))
                val authState by authViewModel.uiState.collectAsStateWithLifecycle()
                val chatState by chatViewModel.uiState.collectAsStateWithLifecycle()

                IMateApp(
                    authState = authState,
                    chatState = chatState,
                    onEmailInputChanged = authViewModel::updateEmailInput,
                    onPasswordInputChanged = authViewModel::updatePasswordInput,
                    onEmailPasswordLogin = authViewModel::loginByEmailPassword,
                    onGoogleLogin = { GoogleCredentialClient.getGoogleIdToken(this@MainActivity) },
                    onGoogleLoginToken = authViewModel::loginByGoogleToken,
                    onSendChat = {
                        chatViewModel.sendMessage(authState.officialAssistantEnabled)
                    },
                    onChatInputChanged = chatViewModel::updateInput,
                    onClearChat = chatViewModel::clearMessages,
                    onToggleOfficialAssistant = authViewModel::setOfficialAssistantEnabled,
                    onLogout = authViewModel::logout,
                )
            }
        }
    }
}
