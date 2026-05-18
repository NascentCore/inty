//
//  APIEndPoint.swift
//  imate
//
//  Created by 天之行 on 2026/4/26.
//

import Foundation

enum HTTPMethod: String {
    case GET
    case POST
    case PUT
    case DELETE
    case PATCH
}

protocol APIEndpoint {
    
    var baseURL: String { get }
    var path: String { get }
    var method: HTTPMethod { get }
    
    var headers: [String: String]? { get }
    var queryItems: [URLQueryItem]? { get }
    
    var body: Data? { get }
}

// 提供默认实现（可选参数不用每次都写）
extension APIEndpoint {
    
    var headers: [String: String]? { nil }
    
    var queryItems: [URLQueryItem]? { nil }
    
    var body: Data? { nil }
}
