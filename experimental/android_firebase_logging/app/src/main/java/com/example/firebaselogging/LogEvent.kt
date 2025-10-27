package com.example.firebaselogging

/**
 * 日志事件数据类
 * 用于定义不同类型的日志事件
 */
data class LogEvent(
    val name: String,
    val parameters: Map<String, Any> = emptyMap(),
    val timestamp: Long = System.currentTimeMillis()
) {
    companion object {
        // 预定义的事件名称
        const val EVENT_APP_OPENED = "app_opened"
        const val EVENT_BUTTON_CLICKED = "button_clicked"
        const val EVENT_CUSTOM_EVENT = "custom_event"
        const val EVENT_CRASH_TEST = "crash_test"
        const val EVENT_PERFORMANCE_TEST = "performance_test"
        const val EVENT_USER_PROPERTY_SET = "user_property_set"
        
        // 预定义的参数键
        const val PARAM_BUTTON_NAME = "button_name"
        const val PARAM_EVENT_NAME = "event_name"
        const val PARAM_EVENT_VALUE = "event_value"
        const val PARAM_USER_ID = "user_id"
        const val PARAM_PROPERTY_KEY = "property_key"
        const val PARAM_PROPERTY_VALUE = "property_value"
        const val PARAM_TIMESTAMP = "timestamp"
        const val PARAM_APP_VERSION = "app_version"
        const val PARAM_DEVICE_MODEL = "device_model"
    }
}