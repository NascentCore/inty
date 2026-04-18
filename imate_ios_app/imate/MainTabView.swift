//
//  MainTabView.swift
//  imate
//
//  Created by 天之行 on 2026/4/18.
//

import SwiftUI


struct MainTabView: View {
    @StateObject private var router = NavigationRouter()

    var body: some View {
        NavigationStack(path: $router.path) {
            TabView {
                HomeView()
                    .tabItem{ Label("我的", systemImage: "person") }
                
//                ProfileView()
//                    .tabItem { Label("我的", systemImage: "person") }
            }
            .navigationDestination(for: AppRoute.self) { route in
                // 统一的路由分发中心
//                switch route {
//                case .productDetail(let id):
//                    ProductDetailView(productId: id)
//                case .userProfile(let name):
//                    UserProfileView(name: name)
//                case .settings:
//                    SettingsView()
//                }
            }
        }
        .environmentObject(router) // 注入环境变量，让子页面随时调用跳转
    }
}
