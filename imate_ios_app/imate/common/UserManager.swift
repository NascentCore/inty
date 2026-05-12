//
//  UserManager.swift
//  imate
//
//  Created by 天之行 on 2026/4/22.
//

import Combine

// 用户单例
class UserManager: ObservableObject {
    static let shared = UserManager()
    private init() {}
    
    @Published var token: String = ""
    
    @Published var avatar: String?
    @Published var email: String = ""
    @Published var isLoggedIn: Bool = false
    
    var agentId: String = ""
    
    func login(name: String) {
        isLoggedIn = true
    }
}
