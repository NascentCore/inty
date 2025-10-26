package com.ai.intellimate

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith

/**
 * 仪器测试，将在 Android 设备上执行。
 *
 * 请参见[测试文档](http://d.android.com/tools/testing)。*/
@RunWith(AndroidJUnit4::class)
class ExampleInstrumentedTest {
    @Test
    fun useAppContext() {
// 被测应用程序的上下文。
        val appContext = InstrumentationRegistry.getInstrumentation().targetContext
        assertEquals("com.ai.intellimate", appContext.packageName)
    }
}
