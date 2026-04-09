package com.ai.imate.main.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation3.runtime.NavKey
import com.ai.core.http.di.KtorHttpClientSingleton
import com.ai.imate.account.data.AuthRepository
import com.ai.imate.account.navigation.Login
import com.ai.imate.chat.Chat
import com.ai.imate.chat.InitChat
import com.ai.imate.chat.data.InitChatOnboardingRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.emitAll
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.stateIn

@HiltViewModel
class MainViewModel
@Inject
constructor(
    private val authRepository: AuthRepository,
    private val initChatOnboardingRepository: InitChatOnboardingRepository,
) : ViewModel() {
    val token = authRepository.token.stateIn(viewModelScope, SharingStarted.Eagerly, "")
    val isLogin = authRepository.isLogin.distinctUntilChanged()

    val initChatOnboardingCompleted =
        initChatOnboardingRepository.onboardingCompleted.distinctUntilChanged()

    init {
        KtorHttpClientSingleton.setBearerTokenProvider { token.value }
    }

    /**
     * 首次为 null：等待登录态与引导状态都至少发出一次后再展示界面，避免冷启动先闪登录页再跳转。
     * 之后为 [Login] / [InitChat] / [Chat]。
     */
    val navigationDestination: StateFlow<NavKey?> =
        flow {
            emit(null)
            emitAll(
                combine(
                    authRepository.isLogin,
                    initChatOnboardingRepository.onboardingCompleted,
                ) { loggedIn, initDone ->
                    when {
                        !loggedIn -> Login
                        !initDone -> InitChat
                        else -> Chat
                    }
                },
            )
        }.stateIn(
            viewModelScope,
            SharingStarted.WhileSubscribed(5000),
            null,
        )

    suspend fun isInitChatOnboardingCompleted(): Boolean =
        initChatOnboardingRepository.isOnboardingCompleted()

    suspend fun setInitChatOnboardingCompleted(completed: Boolean) {
        initChatOnboardingRepository.setOnboardingCompleted(completed)
    }
}