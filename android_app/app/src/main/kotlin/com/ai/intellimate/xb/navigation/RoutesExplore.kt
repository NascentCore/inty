package com.ai.intellimate.xb.navigation

import java.net.URLEncoder

object RoutesExplore {
    // 打榜排行榜页面
    const val BoostLeaderboard = "boost_leaderboard"

    /**
     * 角色专区详情页面路由，参数：themeId（专区ID）、themeTitle（专区标题）、themeDescription（专区描述）、isChristmas（是否为圣诞主题）、agentsJson（角色列表JSON）
     */
    const val CollectionDetail = "collection_detail/{themeId}/{themeTitle}/{themeDescription}/{isChristmas}/{agentsJson}"


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