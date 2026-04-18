//
//  AppRoute.swift
//  imate
//
//  Created by 天之行 on 2026/4/18.
//

import SwiftUI
import Combine


enum AppRoute: Hashable {
    case productDetail(id: String)
    case userProfile(username: String)
    case settings
}

class NavigationRouter: ObservableObject {
    @Published var path = NavigationPath() // 存储导航栈数据
    
    func push(_ route: AppRoute) {
        path.append(route)
    }
    
    func popToRoot() {
        path.removeLast(path.count)
    }
}
