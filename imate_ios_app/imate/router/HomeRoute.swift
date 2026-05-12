//
//  HomeRoute.swift
//  imate
//
//  Created by 天之行 on 2026/5/12.
//

//
//  AppRoute.swift
//  imate
//
//  Created by 天之行 on 2026/4/18.
//

import SwiftUI
import Combine


enum HomeRoute: Hashable {
    case chatPage
}

class RouterHome: ObservableObject {
    @Published var path = NavigationPath() // 存储导航栈数据
    
    // 返回上一级
    func pop() {
        if !path.isEmpty {
            path.removeLast()
        }
    }
    
    func push(_ route: HomeRoute) {
        path.append(route)
    }
    
    func popToRoot() {
        path.removeLast(path.count)
    }
}
