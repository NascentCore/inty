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
    
    var baseURL: String {
        return "https://dev.imate.inty.cc"
    }
    
    var path: String {
        switch self {
        case .login: return "/api/v1/auth/google/login"
        case .profile: return "/profile"
        }
    }
    
    var method: HTTPMethod {
        switch self {
        case .login: return .POST
        case .profile: return .GET
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
        default:
            return nil
        }
    }
}
