package com.ai.inty.utils

import com.ai.inty.beans.AgentInfo


val TEMPLATE_VARIRABLE_REGEX = "\\{\\{\\s*([^}]+)\\s*\\}\\}".toRegex()

/**
 * 便捷函数，用于快速渲染模板
 * @param template 模板字符串
 * @param variables 变量映射表
 * @return 渲染结果
 */
fun renderTemplate(template: String, variables: Map<String, Any>): String {
    var result = template
    // 替换所有匹配的变量
    result = TEMPLATE_VARIRABLE_REGEX.replace(result) { matchResult ->
        val variableName = matchResult.groupValues[1].trim()
        variables[variableName]?.toString() ?: matchResult.value
    }
    return result
}

/**
 * 检查字符串是否包含模板语法 {{ }}
 * @param text 要检查的字符串
 * @return 如果包含模板语法返回true，否则返回false
 */
fun hasTemplateVariable(text: String): Boolean {
    return text.contains("{{") && text.contains("}}")
}

/**
 * 渲染agent的intro或opening文本，如果包含模板语法则进行渲染
 * @param text 原始文本
 * @param agentInfo agent信息，用于提供模板变量
 * @return 渲染后的文本
 */
fun renderAgentText(text: String, agentInfo: AgentInfo, userName: String): String {
    if (!hasTemplateVariable(userName)) {
        return text
    }
    // 构建模板变量映射
    val variables = mapOf(
        "char" to agentInfo.name,
        "user" to userName,
    )
    return renderTemplate(text, variables)
}
