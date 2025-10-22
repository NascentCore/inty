package com.ai.inty.base

/**
 * ViewModel事件类型
 */
sealed class ViewModelEvent {
    /**
     * 关闭Activity事件
     */
    object CloseActivity : ViewModelEvent()

    /**
     * 操作成功事件
     */
    object OperationSuccess : ViewModelEvent()

    /**
     * 登录成功事件
     */
    object LoginSuccess : ViewModelEvent()

    /**
     * 用户信息更新成功事件
     */
    object UserProfileUpdated : ViewModelEvent()

    /**
     * 举报提交成功事件
     */
    object ReportSubmitted : ViewModelEvent()
}
