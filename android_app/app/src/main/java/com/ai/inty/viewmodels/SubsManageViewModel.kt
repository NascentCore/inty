package com.ai.inty.viewmodels

import androidx.lifecycle.viewModelScope
import com.ai.inty.base.BaseViewModel
import com.inty.utils.log.EasyLog
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.launch

/** 定义一个事件类，用于ViewModel向View发送指令 */
sealed class SubscriptionUiEvent {
  object NavigateToPlayStoreSubscriptions : SubscriptionUiEvent()

  // 可以添加其他UI事件，例如显示错误Toast等
  data class ShowToast(val message: String) : SubscriptionUiEvent()
}

/** 订阅管理页面 ViewModel */
class SubsManageViewModel : BaseViewModel() {

  private val _uiEvent = MutableSharedFlow<SubscriptionUiEvent>()
  val uiEvent: SharedFlow<SubscriptionUiEvent> = _uiEvent

  /** 触发跳转到 Google Play 订阅管理页面的事件。 ViewModel 不直接执行跳转，而是通知 View 去执行。 */
  fun navigateToGooglePlaySubscription() {
    viewModelScope.launch {
      try {
        // ViewModel只负责逻辑判断和事件发出
        // 具体的Intent启动逻辑由View层负责
        _uiEvent.emit(SubscriptionUiEvent.NavigateToPlayStoreSubscriptions)
        EasyLog.log("✅ ViewModel发出跳转 Google Play 订阅管理页面的事件")
      } catch (e: Exception) {
        EasyLog.log("❌ 发送跳转事件失败: ${e.message}")
        // 也可以发出一个事件让View显示错误信息
        _uiEvent.emit(SubscriptionUiEvent.ShowToast("无法处理跳转请求。"))
      }
    }
  }
}
