//
//  UserAPI.swift
//  imate
//
//  Created by 天之行 on 2026/4/26.
//

import Foundation

enum UserAPI: APIEndpoint {
    
    case login(email: String, password: String)
    case profile
    
    case creatAvatar(prompt: String)
    case creatAgent(name: String, gender: String, avatar: String, intro: String)
    
    var baseURL: String {
        return "https://dev.imate.inty.cc"
    }
    
    var path: String {
        switch self {
        case .login: return "/api/v1/auth/google/login"
        case .profile: return "/profile"
            
        case .creatAvatar: return "/api/v1/ai/agents/text-to-image"
        case .creatAgent: return "/api/v1/ai/agents"
        }
    }
    
    var method: HTTPMethod {
        switch self {
        case .login: return .POST
        case .profile: return .GET
            
        case .creatAvatar: return .POST
        case .creatAgent: return .POST
        }
    }
    
    var body: Data? {
        switch self {
        case let .login(email, password):
            let dict = [
                "email": email,
                "password": password
            ]
            return try? JSONSerialization.data(withJSONObject: dict)
        case let .creatAvatar(prompt):
            let dict = ["prompt": prompt]
            return try? JSONSerialization.data(withJSONObject: dict)
        case let .creatAgent(name, gender, avatar, intro):
            let dict = [
                "opening": "",
                "visibility": "PRIVATE",
                "name": name,
                "gender": gender,
                "avatar": avatar,
                "intro": intro
            ]
            return try? JSONSerialization.data(withJSONObject: dict)
        default:
            return nil
        }
    }
}
