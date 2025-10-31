package com.example.firebaseremoteconfig

import androidx.compose.ui.graphics.Color

/**
 * AB 测试变体定义
 */
enum class ABTestVariant(
    val value: String,
    val displayName: String,
    val buttonColor: Color
) {
    CONTROL("control", "对照组", Color(0xFF6200EE)), // 默认紫色
    VARIANT_A("variant_a", "变体 A", Color(0xFF2196F3)), // 蓝色
    VARIANT_B("variant_b", "变体 B", Color(0xFFF44336)); // 红色
    
    companion object {
        fun fromString(value: String): ABTestVariant {
            return values().find { it.value == value } ?: CONTROL
        }
    }
}
