//
//  Key.swift
//  imate
//
//  Created by 天之行 on 2026/5/11.
//

import Foundation
import Security

enum SaveKeys: String {
    case token
    case agentId
    
    var key: String {
        switch self {
        case .token: return "token"
        case .agentId: return "agentId"
        }
    }
}

final class KeychainManager {

    static let shared = KeychainManager()

    private init() {}

    // MARK: - Save

    func save(key: String, value: String) {

        let data = value.data(using: .utf8)!

        // 删除旧数据
        delete(key: key)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]

        SecItemAdd(query as CFDictionary, nil)
    }

    // MARK: - Read

    func read(key: String) -> String? {

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?

        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess else {
            return nil
        }

        guard let data = result as? Data else {
            return nil
        }

        return String(data: data, encoding: .utf8)
    }

    // MARK: - Delete

    func delete(key: String) {

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key
        ]

        SecItemDelete(query as CFDictionary)
    }
}
