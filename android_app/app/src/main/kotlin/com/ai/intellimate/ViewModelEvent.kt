package com.ai.intellimate

/**
 * ViewModel事件类型
 */
sealed class ViewModelEvent {

    /**
     * 登录成功事件
     */
    object LoginSuccess : ViewModelEvent()

    /**
     * 需要完善注册信息事件
     */
    object NeedRegInfo : ViewModelEvent()

    /**
     * 用户信息更新成功事件
     */
    object UserProfileUpdated : ViewModelEvent()

    /**
     * 举报提交成功事件
     */
    object ReportSubmitted : ViewModelEvent()
}
