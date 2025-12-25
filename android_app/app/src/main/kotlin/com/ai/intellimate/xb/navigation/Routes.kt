package com.ai.intellimate.xb.navigation

/**
 * 应用路由定义
 *
 * 定义应用内所有页面的导航路由路径，使用 Compose Navigation 进行页面跳转。 所有路由路径使用小写下划线命名风格（snake_case）。
 */
object Routes {
    const val SplashLogin = "splash_login"
    const val HomeTab = "home_screen"

    val Chat = RoutesChat
    val Me = RoutesMe
    val Explore = RoutesExplore
    val Home = RoutesHome
}
