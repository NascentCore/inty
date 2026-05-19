//
//  Home.swift
//  imate
//
//  Created by 天之行 on 2026/5/12.
//

import SwiftUI

struct HomeView: View {
    // 初始化 Router
    @StateObject private var routerHome = RouterHome()
    @StateObject var userManager = UserManager.shared
    
    var body: some View {
        // 将 path 绑定到 NavigationStack
        NavigationStack(path: $routerHome.path) {
            ChatPage()
            
            // 统一配置跳转逻辑
            .navigationDestination(for: HomeRoute.self) { route in
                switch route {
                case .chatPage:
                    ChatPage()
                }
            }
        }
        // 注入环境对象，子页面通过 @EnvironmentObject 获取
        .environmentObject(routerHome)
        .environmentObject(userManager)
   
    }
}
