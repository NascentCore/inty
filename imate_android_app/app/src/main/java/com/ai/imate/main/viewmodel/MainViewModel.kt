package com.ai.imate.main.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation3.runtime.NavKey
import com.ai.core.http.di.KtorHttpClientSingleton
import com.ai.imate.account.AuthPostLoginNavigationGate
import com.ai.imate.account.data.AuthRepository
import com.ai.imate.account.navigation.Login
import com.ai.imate.chat.Chat
import com.ai.imate.chat.InitChat
import com.ai.imate.chat.data.ChatMainRepository
import com.ai.imate.chat.data.InitChatOnboardingRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

@HiltViewModel
class MainViewModel
@Inject
constructor(
    private val authRepository: AuthRepository,
    private val initChatOnboardingRepository: InitChatOnboardingRepository,
    private val chatMainRepository: ChatMainRepository,
    private val authPostLoginNavigationGate: AuthPostLoginNavigationGate,
) : ViewModel() {
    val token = authRepository.token.stateIn(viewModelScope, SharingStarted.Eagerly, "")
    val isLogin = authRepository.isLogin.distinctUntilChanged()

    val initChatOnboardingCompleted =
        initChatOnboardingRepository.onboardingCompleted.distinctUntilChanged()

    init {
        KtorHttpClientSingleton.setBearerTokenProvider { token.value }
        viewModelScope.launch(Dispatchers.IO) { chatMainRepository.connectWebSocketWhenLoggedIn() }
    }

    /**
     * 首次为 null：等待登录态与引导状态都至少发出一次后再展示界面，避免冷启动先闪登录页再跳转。
     * 之后为 [Login] / [InitChat] / [Chat]。本地已有 companion（onboarding 完成）时，重新登录后会进入 [Chat]。
     */
    val navigationDestination: StateFlow<NavKey?> =
        flow {
            emit(null)
            emitAll(
                combine(
                    authRepository.isLogin,
                    initChatOnboardingRepository.onboardingCompleted,
                    authPostLoginNavigationGate.holdPostLoginNavigation,
                ) { loggedIn, initDone, holdPostLogin ->
                    when {
                        !loggedIn -> Login
                        holdPostLogin -> Login
                        !initDone -> InitChat
                        else -> Chat
                    }
                },
            )
        }.stateIn(
            viewModelScope,
            SharingStarted.Eagerly,
            null,
        )

    suspend fun isInitChatOnboardingCompleted(): Boolean =
        initChatOnboardingRepository.isOnboardingCompleted()

    fun onEmailAuthLoadingFinished() {
        authPostLoginNavigationGate.releaseHold()
    }
}
