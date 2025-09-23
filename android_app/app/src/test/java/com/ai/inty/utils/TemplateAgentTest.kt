package com.ai.inty.utils

import com.ai.inty.beans.AgentInfo
import org.junit.Test
import org.junit.Assert.*

/**
 * 测试 agent 文本模板渲染功能
 */
class TemplateAgentTest {
    
    @Test
    fun testRenderAgentTextWithTemplate() {
        val agentInfo = AgentInfo(
            id = "test-agent-1",
            name = "Alice",
            intro = "Hello, I'm {{ char }}! Nice to meet you, {{ user }}!",
            opening = "Welcome! I'm {{ agent_name }} and I'm here to help you."
        )
        
        // 测试 intro 渲染
        val renderedIntro = renderAgentText(agentInfo.intro, agentInfo)
        assertEquals("Hello, I'm Alice! Nice to meet you, User!", renderedIntro)
        
        // 测试 opening 渲染
        val renderedOpening = renderAgentText(agentInfo.opening, agentInfo)
        assertEquals("Welcome! I'm Alice and I'm here to help you.", renderedOpening)
    }
    
    @Test
    fun testRenderAgentTextWithoutTemplate() {
        val agentInfo = AgentInfo(
            id = "test-agent-2",
            name = "Bob",
            intro = "Hello, I'm Bob! Nice to meet you!",
            opening = "Welcome! I'm here to help you."
        )
        
        // 测试没有模板语法的文本
        val renderedIntro = renderAgentText(agentInfo.intro, agentInfo)
        assertEquals("Hello, I'm Bob! Nice to meet you!", renderedIntro)
        
        val renderedOpening = renderAgentText(agentInfo.opening, agentInfo)
        assertEquals("Welcome! I'm here to help you.", renderedOpening)
    }
    
    @Test
    fun testRenderAgentTextWithNullAgent() {
        val text = "Hello, I'm {{ char }}!"
        val renderedText = renderAgentText(text, null)
        assertEquals(text, renderedText) // 应该返回原始文本
    }
    
    @Test
    fun testRenderAgentTextWithEmptyText() {
        val agentInfo = AgentInfo(
            id = "test-agent-3",
            name = "Charlie"
        )
        
        val renderedText = renderAgentText("", agentInfo)
        assertEquals("", renderedText)
    }
    
    @Test
    fun testHasTemplateSyntax() {
        assertTrue(hasTemplateSyntax("Hello {{ char }}!"))
        assertTrue(hasTemplateSyntax("{{ user }} and {{ char }}"))
        assertFalse(hasTemplateSyntax("Hello world!"))
        assertFalse(hasTemplateSyntax("Hello { char }!")) // 单花括号
        assertFalse(hasTemplateSyntax("Hello {{ char")) // 不完整
    }
}
