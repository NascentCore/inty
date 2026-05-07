//
//  NetworkService.swift
//  imate
//
//  Created by 天之行 on 2026/4/26.
//

import Foundation

// 通用返回结构（后端统一格式）
struct APIResponse<T: Decodable>: Decodable {
    let code: Int
    let message: String
    let data: T?
}

final class NetworkService {
    
    static let shared = NetworkService()
    
    private init() {}
    
    func request<T: Decodable>(
        _ endpoint: APIEndpoint,
        decoder: JSONDecoder = JSONDecoder()
    ) async throws -> T {
        
        // 1. 构建 URL
        guard var urlComponents = URLComponents(string: endpoint.baseURL + endpoint.path) else {
            throw SLNetworkError.invalidURL
        }
        
        urlComponents.queryItems = endpoint.queryItems
        
        guard let url = urlComponents.url else {
            throw SLNetworkError.invalidURL
        }
        
        // 2. 构建 Request
        var request = URLRequest(url: url)
        request.httpMethod = endpoint.method.rawValue
        request.httpBody = endpoint.body
        
        // 默认 JSON
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(UserManager.shared.token)", forHTTPHeaderField: "Authorization")
        
        // 测试用
//        let token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3Nzg3NTUzMjAsInN1YiI6InVzZXItMDFLUEFITU5XUDYzNUpSWUFXWUdEUzNQUlMifQ.ptxNPNK_Oc7Hs3kUV6ptOmrOnVVgnt7P65colSTvgCc"
//        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        
        // 自定义 Header
        endpoint.headers?.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }
        
        do {
            // 3. 发起请求
            let (data, response) = try await URLSession.shared.data(for: request)
            
            // 4. 校验响应
            guard let httpResponse = response as? HTTPURLResponse else {
                throw SLNetworkError.invalidResponse
            }
            
            guard (200...299).contains(httpResponse.statusCode) else {
                throw SLNetworkError.statusCode(httpResponse.statusCode)
            }
            
            // 👉 Debug 打印
            #if DEBUG
            if let raw = String(data: data, encoding: .utf8) {
                print("✅ Raw Response:\n\(raw)")
            }
            #endif
            
            // 5️⃣ 解析为通用结构
            let apiResponse = try decoder.decode(APIResponse<T>.self, from: data)
            
            // 6️⃣ 业务状态判断
            if apiResponse.code != 200 {
                throw SLNetworkError.serverError(apiResponse.message)
            }
            
            // 7️⃣ 取 data
            guard let result = apiResponse.data else {
                throw SLNetworkError.emptyData
            }
            
            return result
            
        } catch let error as SLNetworkError {
            throw error
        } catch {
            throw SLNetworkError.unknown(error)
        }
    }
}
