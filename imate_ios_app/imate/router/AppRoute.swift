//
//  AppRoute.swift
//  imate
//
//  Created by 天之行 on 2026/4/18.
//

import SwiftUI
import Combine


enum AppRoute: Hashable {
    case login
    case home
    
    case loginEmail
    case loginEmailPassword
    case loginAuth
}

class Router: ObservableObject {
    @Published var path = NavigationPath() // 存储导航栈数据
    
    // 返回上一级
    func pop() {
        if !path.isEmpty {
            path.removeLast()
        }
    }
    
    func push(_ route: AppRoute) {
        path.append(route)
    }
    
    func popToRoot() {
        path.removeLast(path.count)
    }
}
