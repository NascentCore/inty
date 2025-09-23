package com.ai.inty.utils

import org.junit.Test
import org.junit.Assert.*
import kotlin.math.exp

/**
 * 模板渲染函数测试用例
 * 展示 TemplateRenderer 的各种使用场景
 */
class TemplateTest {
    @Test
    fun testBasicTemplateRendering() {
        // 测试基本模板渲染功能
        val variables = mapOf(
            "char" to "intellimate",
            "user" to "dx"
        )
        val result1 = renderTemplate("!!!{{  char  }} and {{  user  }}!!!", variables)
        val expected = "!!!intellimate and dx!!!"
        assertEquals(expected, result1)
        // 测试无空格的变量名
        val result2 = renderTemplate("!!!{{char}} and {{user}}!!!", variables)
        assertEquals(expected, result2)

        val result3 = renderTemplate("!!!{{ char }} and {{ user }}!!!", variables)
        assertEquals(expected, result3)
    }
}
