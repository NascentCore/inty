//
//  NetworkError.swift
//  imate
//
//  Created by 天之行 on 2026/4/26.
//

import Foundation

enum SLNetworkError: Error, LocalizedError {
    
    case invalidURL
    case invalidResponse
    case statusCode(Int)
    case decodeError
    case unknown(Error)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "无效的URL"
        case .invalidResponse:
            return "无效的服务器响应"
        case .statusCode(let code):
            return "请求失败，状态码：\(code)"
        case .decodeError:
            return "数据解析失败"
        case .unknown(let error):
            return error.localizedDescription
        }
    }
}
