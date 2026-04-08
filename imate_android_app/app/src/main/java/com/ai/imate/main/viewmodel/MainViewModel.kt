package com.ai.imate.main.viewmodel

import androidx.lifecycle.ViewModel
import com.ai.imate.account.data.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.distinctUntilChanged
import javax.inject.Inject

@HiltViewModel
class MainViewModel @Inject constructor(
    private val authRepository: AuthRepository
): ViewModel() {
    val isLogin = authRepository.isLogin.distinctUntilChanged()
}