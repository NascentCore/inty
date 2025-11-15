package com.ai.intellimate.testing

import ai.sxwl.android.utils.LogUtils
import io.mockk.Runs
import io.mockk.anyVararg
import io.mockk.every
import io.mockk.mockkObject
import io.mockk.unmockkObject

/**
 * 简化 LogUtils 的 mock，避免在 JVM 测试中触发真实的 Android 日志依赖。
 */
object LogUtilsTestHelper {

    fun mock() {
        mockkObject(LogUtils)
        every { LogUtils.d(*anyVararg()) } just Runs
        every { LogUtils.i(*anyVararg()) } just Runs
        every { LogUtils.w(*anyVararg()) } just Runs
        every { LogUtils.e(*anyVararg()) } just Runs
    }

    fun unmock() {
        unmockkObject(LogUtils)
    }
}
