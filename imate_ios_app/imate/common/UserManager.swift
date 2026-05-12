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
    
    @Published var token: String?
    @Published var agentId: String?
    
    @Published var avatar: String?
    @Published var email: String = ""
    @Published var isLoggedIn: Bool = false
    
    var isLogin: Bool {
        token != nil && agentId != nil
    }
    
    private init() {
        self.token = KeychainManager.shared.read(key: SaveKeys.token.key) ?? nil
        self.agentId = KeychainManager.shared.read(key: SaveKeys.agentId.key) ?? nil
        print("on self token val is- -------->\(self.token ?? "")----->")
    }
    
    func setToken(s: String) {
        self.token = s
        KeychainManager.shared.save(key: SaveKeys.token.key, value: s)
    }
    
    func setAgentId(s: String) {
        self.agentId = s
        KeychainManager.shared.save(key: SaveKeys.agentId.key, value: s)
    }
    
    func logout() {
        token = nil
        agentId = nil
        KeychainManager.shared.delete(key: SaveKeys.agentId.key)
        KeychainManager.shared.delete(key: SaveKeys.token.key)
    }
}
