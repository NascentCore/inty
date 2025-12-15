package com.ai.intellimate.xb.navigation

import java.net.URLEncoder

/**
 * 应用路由定义
 *
 * 定义应用内所有页面的导航路由路径，使用 Compose Navigation 进行页面跳转。 所有路由路径使用小写下划线命名风格（snake_case）。
 */
object Routes {
    /** 启动/登录页面路由 */
    const val SplashLogin = "splash_login"

    /** 主页标签页路由（包含 Explore、Messages、Me 等底部导航） */
    const val HomeTab = "home_screen"

    /** 聊天页面路由，参数：agentId（角色ID）、showBoost（是否显示Boost弹窗） */
    const val ChatPage = "chat_page/{agentId}/{showBoost}"

    /** 设置页面路由 */
    const val Settings = "settings"

    /** VIP订阅中心页面路由 */
    const val VipCenter = "vip_center"

    /** 签到页面路由 */
    const val CheckIn = "check_in"

    /** 编辑个人资料页面路由 */
    const val EditProfile = "ef"

    const val BoostLeaderboard = "boost_leaderboard"
    const val AgentInfoPage = "agent_info_page/{agentId}"
    const val AgentPhotoAlbum = "agent_photo_album/{agentId}"

    /**
     * 角色专区详情页面路由，参数：themeId（专区ID）、themeTitle（专区标题）、themeDescription（专区描述）、isChristmas（是否为圣诞主题）、agentsJson（角色列表JSON）
     */
    const val CollectionDetail =
        "collection_detail/{themeId}/{themeTitle}/{themeDescription}/{isChristmas}/{agentsJson}"

    /**
     * 构建聊天页面路由路径
     *
     * @param agentId 角色ID
     * @param showBoost 是否显示Boost弹窗
     * @return 聊天页面路由路径
     */
    fun chatPage(agentId: String, showBoost: Boolean) = "chat_page/${agentId}/${showBoost}"

    fun agentInfPage(agentId: String) = "agent_info_page/${agentId}"
    fun agentPhotoAlbum(agentId: String) = "agent_photo_album/${agentId}"

    /**
     * 构建角色专区详情页面路由路径
     *
     * 使用 URL 编码处理参数，确保特殊字符能正确传递。
     *
     * @param themeId 专区ID
     * @param themeTitle 专区标题
     * @param themeDescription 专区描述
     * @param isChristmas 是否为圣诞主题
     * @param agentsJson 角色列表的JSON字符串
     * @return 角色专区详情页面路由路径
     */
    fun collectionDetail(
        themeId: String,
        themeTitle: String,
        themeDescription: String,
        isChristmas: Boolean,
        agentsJson: String,
    ): String {
        val encodedTitle = URLEncoder.encode(themeTitle, "UTF-8")
        val encodedDescription = URLEncoder.encode(themeDescription, "UTF-8")
        val encodedAgentsJson = URLEncoder.encode(agentsJson, "UTF-8")
        return "collection_detail/${themeId}/${encodedTitle}/${encodedDescription}/${isChristmas}/${encodedAgentsJson}"
    }
}
