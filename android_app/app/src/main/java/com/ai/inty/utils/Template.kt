package com.ai.inty.utils

/**
 * 简单的模板渲染工具类
 * 支持 {{ variable }} 格式的变量替换
 * 
 * 示例：
 * {{ char }} and {{ user }} are good friends, char=aaa, user=bbb
 * 渲染结果为：aaa and bbb are good friends
 */
object TemplateRenderer {
    /**
     * 渲染模板，替换模版中的包围在 {{}} 中的变量
     * @param template 模板字符串
     * @param variables 变量映射表
     * @return 渲染结果
     */
    fun render(template: String, variables: Map<String, Any>): String {
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
    
    /**
     * 渲染模板，支持默认值语法 {{ variable:defaultValue }}
     * @param template 模板字符串
     * @param variables 变量映射表
     * @return 渲染结果
     */
    fun renderWithDefaults(template: String, variables: Map<String, Any>): String {
        var result = template
        // 使用正则表达式匹配 {{ variable:defaultValue }} 格式的变量
        val pattern = "\\{\\{\\s*([^:}]+)(?::([^}]*))?\\s*\\}\\}".toRegex()
        // 替换所有匹配的变量
        result = pattern.replace(result) { matchResult ->
            val variableName = matchResult.groupValues[1].trim()
            val defaultValue = matchResult.groupValues[2]
            // 如果变量存在，使用变量值；否则使用默认值（即使是空字符串）
            if (variables.containsKey(variableName)) {
                variables[variableName]?.toString() ?: ""
            } else {
                defaultValue
            }
        }
        return result
    }
}

/**
 * 便捷函数，用于快速渲染模板
 * @param template 模板字符串
 * @param variables 变量映射表
 * @return 渲染结果
 */
fun renderTemplate(template: String, variables: Map<String, Any>): String {
    return TemplateRenderer.render(template, variables)
}
