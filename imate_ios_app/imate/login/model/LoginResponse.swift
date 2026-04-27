//
//  LoginResponse.swift
//  imate
//
//  Created by 天之行 on 2026/4/27.
//

struct LoginResponse: Decodable {
    let token: String
    let user: User
}

struct User: Decodable {
    let id: String?
    let nickname: String?
    let avatar: String?
    let email: String?
    let phone: String?
    let authType: String?
    let gender: String?
    let ageGroup: String?
    let systemLanguage: String?
    let description: String?
    let isNewUser: Bool?
    
    enum CodingKeys: String, CodingKey {
        case id
        case nickname
        case avatar
        case email
        case phone
        case authType = "auth_type"
        case gender
        case ageGroup = "age_group"
        case systemLanguage = "system_language"
        case description
        case isNewUser = "is_new_user"
    }
}
