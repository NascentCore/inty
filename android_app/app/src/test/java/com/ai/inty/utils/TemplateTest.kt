package com.ai.inty.utils

import org.junit.Test
import org.junit.Assert.*

/**
 * 模板渲染函数测试用例
 * 展示 TemplateRenderer 的各种使用场景
 */
class TemplateTest {

    @Test
    fun testBasicTemplateRendering() {
        // 测试基本模板渲染功能
        val template = "{{ char }} and {{ user }} are good friends"
        val variables = mapOf(
            "char" to "intellimate",
            "user" to "dx"
        )
        
        val result = renderTemplate(template, variables)
        assertEquals("intellimate and dx are good friends", result)
    }

    @Test
    fun testTemplateWithSpaces() {
        // 测试变量名包含空格的情况
        val template = "{{  char  }} and {{  user  }} are good friends"
        val variables = mapOf(
            "char" to "Alice",
            "user" to "Bob"
        )
        
        val result = renderTemplate(template, variables)
        assertEquals("Alice and Bob are good friends", result)
    }

    @Test
    fun testTemplateWithDifferentDataTypes() {
        // 测试不同类型的数据
        val template = "User {{ name }} has {{ age }} years old and {{ isActive }} status"
        val variables = mapOf(
            "name" to "John",
            "age" to 25,
            "isActive" to true
        )
        
        val result = renderTemplate(template, variables)
        assertEquals("User John has 25 years old and true status", result)
    }

    @Test
    fun testTemplateWithMissingVariables() {
        // 测试缺少变量的情况
        val template = "{{ existing }} and {{ missing }} variables"
        val variables = mapOf("existing" to "found")
        
        val result = renderTemplate(template, variables)
        assertEquals("found and {{ missing }} variables", result)
    }


    @Test
    fun testTemplateWithSpecialCharacters() {
        // 测试特殊字符
        val template = "Message: {{ message }}"
        val variables = mapOf("message" to "Hello, World! @#$%^&*()")
        
        val result = renderTemplate(template, variables)
        assertEquals("Message: Hello, World! @#$%^&*()", result)
    }

    @Test
    fun testTemplateWithEmptyString() {
        // 测试空字符串模板
        val template = ""
        val variables = mapOf("any" to "value")
        
        val result = renderTemplate(template, variables)
        assertEquals("", result)
    }

    @Test
    fun testTemplateWithNoVariables() {
        // 测试没有变量的模板
        val template = "This is a plain text without variables"
        val variables = mapOf("any" to "value")
        
        val result = renderTemplate(template, variables)
        assertEquals("This is a plain text without variables", result)
    }

    @Test
    fun testTemplateRendererObject() {
        // 测试直接使用 TemplateRenderer 对象
        val template = "{{ greeting }} {{ name }}"
        val variables = mapOf(
            "greeting" to "Hello",
            "name" to "World"
        )
        
        val result = TemplateRenderer.render(template, variables)
        assertEquals("Hello World", result)
    }

    @Test
    fun testRealWorldChatMessage() {
        // 测试真实世界的聊天消息模板
        val template = "{{ charName }}: {{ message }}"
        val variables = mapOf(
            "charName" to "AI Assistant",
            "message" to "Hello! How can I help you today?"
        )
        
        val result = renderTemplate(template, variables)
        assertEquals("AI Assistant: Hello! How can I help you today?", result)
    }
}
