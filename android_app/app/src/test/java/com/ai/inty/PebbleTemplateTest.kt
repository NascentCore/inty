package com.ai.inty

import org.junit.Test
import org.junit.Assert.assertEquals

/**
 * 极简模板引擎演示
 * 演示 Jinja2 风格的模板渲染概念
 */
class PebbleTemplateTest {

    /**
     * 简单的模板渲染函数
     * 模拟 Jinja2 的 {{ variable }} 语法
     */
    private fun renderTemplate(template: String, variables: Map<String, Any>): String {
        var result = template
        
        // 替换 {{ variable }} 格式的变量
        variables.forEach { (key, value) ->
            val placeholder = "{{ $key }}"
            result = result.replace(placeholder, value.toString())
        }
        
        return result
    }

    @Test
    fun testSimpleTemplateRendering() {
        // 定义模板字符串 - 使用 Jinja2 风格的 {{ }} 语法
        val templateString = "{{ char }} and {{ user }} are good friends"
        
        // 准备上下文数据
        val context = mapOf(
            "char" to "intellimate",
            "user" to "dx"
        )
        
        // 渲染模板
        val result = renderTemplate(templateString, context)
        
        // 验证结果
        val expected = "intellimate and dx are good friends"
        assertEquals("模板渲染结果应该正确", expected, result)
        
        println("模板: $templateString")
        println("变量: char=intellimate, user=dx")
        println("结果: $result")
    }
    
    @Test
    fun testTemplateWithNumbers() {
        // 定义包含数字的模板
        val templateString = "{{ char }} has {{ level }} level and {{ score }} points!"
        
        // 准备上下文数据
        val context = mapOf(
            "char" to "intellimate",
            "level" to 100,
            "score" to 9999
        )
        
        // 渲染模板
        val result = renderTemplate(templateString, context)
        
        // 验证结果
        val expected = "intellimate has 100 level and 9999 points!"
        assertEquals("数字模板渲染结果应该正确", expected, result)
        
        println("数字模板: $templateString")
        println("结果: $result")
    }
    
    @Test
    fun testTemplateWithMultipleOccurrences() {
        // 定义包含重复变量的模板
        val templateString = "{{ char }} is awesome! {{ char }} is the best character!"
        
        // 准备上下文数据
        val context = mapOf(
            "char" to "intellimate"
        )
        
        // 渲染模板
        val result = renderTemplate(templateString, context)
        
        // 验证结果
        val expected = "intellimate is awesome! intellimate is the best character!"
        assertEquals("重复变量模板渲染结果应该正确", expected, result)
        
        println("重复变量模板: $templateString")
        println("结果: $result")
    }
    
    @Test
    fun testTemplateWithMissingVariables() {
        // 定义包含未定义变量的模板
        val templateString = "{{ char }} and {{ user }} are friends, but {{ missing }} is not defined"
        
        // 准备部分上下文数据
        val context = mapOf(
            "char" to "intellimate",
            "user" to "dx"
        )
        
        // 渲染模板
        val result = renderTemplate(templateString, context)
        
        // 验证结果 - 未定义的变量应该保持原样
        val expected = "intellimate and dx are friends, but {{ missing }} is not defined"
        assertEquals("未定义变量应该保持原样", expected, result)
        
        println("未定义变量模板: $templateString")
        println("结果: $result")
    }
}
