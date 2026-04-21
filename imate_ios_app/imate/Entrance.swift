//
//  Entrance.swift
//  imate
//
//  Created by 天之行 on 2026/4/19.
//

import SwiftUI

struct Entrance: View {
    // 初始化 Router
    @StateObject private var router = Router()
    
    var body: some View {
        // 将 path 绑定到 NavigationStack
        NavigationStack(path: $router.path) {
            LoginView()
            // 统一配置跳转逻辑
            .navigationDestination(for: AppRoute.self) { route in
                switch route {
                case .login:
                    LoginView()
                case .home:
                    HomeView()
                case .loginEmail:
                    LoginEmail()
                case .loginEmailPassword:
                    LoginEmailPassword()
                case .loginAuth:
                    LoginAuth()
                }
            }
        }
        // 注入环境对象，子页面通过 @EnvironmentObject 获取
        .environmentObject(router)
    }
}
