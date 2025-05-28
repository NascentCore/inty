package com.ai.inty.base

import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

open class BaseViewModel: ViewModel() {
//    private val _snackbar = MutableSharedFlow<String>()
//    val snackbar = _snackbar.asSharedFlow()

    fun showSnackbar(text: String) {
        viewModelScope.launch {
            ToastUtils.showToast(text)
        }
    }
}

open class BaseActivityViewModel : BaseViewModel() {

    private val _finishActivity = MutableStateFlow(false)
    val finishActivity = _finishActivity.asStateFlow()

    fun closeActivity(delayTimeMS: Long = 0) {
        EasyLog.log("closeActivity $this delay=$delayTimeMS")
        viewModelScope.launch(Dispatchers.Main) {
            if (delayTimeMS > 0) {
                delay(delayTimeMS)
            }
            _finishActivity.value = true
        }
    }

}