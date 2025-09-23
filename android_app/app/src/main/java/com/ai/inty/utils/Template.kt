package com.ai.inty.utils

/**
 * 便捷函数，用于快速渲染模板
 * @param template 模板字符串
 * @param variables 变量映射表
 * @return 渲染结果
 */
fun renderTemplate(template: String, variables: Map<String, Any>): String {
    var result = template
    // 使用正则表达式匹配 {{ variable }} 格式的变量
    val pattern = "\\{\\{\\s*([^}]+)\\s*\\}\\}".toRegex()
    // 替换所有匹配的变量
    result = pattern.replace(result) { matchResult ->
        val variableName = matchResult.groupValues[1].trim()
        variables[variableName]?.toString() ?: matchResult.value
    }
    return result
}
