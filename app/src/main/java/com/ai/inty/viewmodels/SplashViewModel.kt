package com.ai.inty.viewmodels

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseActivityViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class SplashViewModel : BaseActivityViewModel() {
    enum class InitState {
        None,
        Initing,
        Success,
        Failed
    }
    private val _initState = MutableStateFlow(InitState.None)
    val initState = _initState.asStateFlow()

    fun initTask() {
        _initState.value = InitState.Initing

        viewModelScope.launch(Dispatchers.IO) {
            delay(3000)

            _initState.value = InitState.Success
        }
    }
}