package com.inty.imate.account.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.core.data.exceptions.GlobalErrorHandler
import com.inty.imate.account.AuthPostLoginNavigationGate
import com.inty.imate.account.data.AuthRepository
import com.inty.imate.account.ui.uistate.LoginUiState
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.CancellationException
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
            try {
                authRepository.googleLogin(idToken)
            } catch (e: CancellationException) {
                authPostLoginNavigationGate.releaseHold()
                setLoading(false)
                throw e
            } catch (e: Exception) {
                GlobalErrorHandler.sendError(e)
                authPostLoginNavigationGate.releaseHold()
                setLoading(false)
            }
        }
    }

    fun emailLogin(email: String, password: String) {
        viewModelScope.launch {
            setLoading(true)
            try {
                authRepository.emailLogin(email, password)
            } catch (e: CancellationException) {
                authPostLoginNavigationGate.releaseHold()
                setLoading(false)
                throw e
            } catch (e: Exception) {
                GlobalErrorHandler.sendError(e)
                authPostLoginNavigationGate.releaseHold()
                setLoading(false)
            }
        }
    }
}

