package com.ai.imate.account.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.ai.core.data.exceptions.globalCatch
import com.ai.imate.account.AuthPostLoginNavigationGate
import com.ai.imate.account.data.AuthRepository
import com.ai.imate.account.ui.uistate.LoginUiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class LoginViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val authPostLoginNavigationGate: AuthPostLoginNavigationGate,
) : ViewModel() {

    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    val isLogin = authRepository.isLogin.distinctUntilChanged()

    fun setLoading(isLoading: Boolean) {
        _uiState.update { it.copy(isLoading = isLoading) }
        if (isLoading) {
            authPostLoginNavigationGate.beginHold()
        }
    }

    fun googleLogin(idToken: String) {
        viewModelScope.launch {
            setLoading(true)
            globalCatch {
                authRepository.googleLogin(idToken)
            }
        }.invokeOnCompletion {
            if (it != null) {
                authPostLoginNavigationGate.releaseHold()
                setLoading(false)
            }
        }
    }

    fun emailLogin(email: String, password: String) {
        viewModelScope.launch {
            setLoading(true)
            globalCatch {
                authRepository.emailLogin(email, password)
            }
        }.invokeOnCompletion {
            if (it != null) {
                authPostLoginNavigationGate.releaseHold()
                setLoading(false)
            }
        }
    }
}

