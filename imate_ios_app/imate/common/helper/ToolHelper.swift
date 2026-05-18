//
//  ToolHelper.swift
//  imate
//
//  Created by 天之行 on 2026/4/23.
//

import Foundation

enum ToolHelper {
    static func isValidEmail(_ email: String) -> Bool {
        let pattern = "[A-Z0-9a-z._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,64}"
        let predicate = NSPredicate(format: "SELF MATCHES %@", pattern)
        return predicate.evaluate(with: email)
    }
}
