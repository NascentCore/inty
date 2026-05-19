//
//  LoginHelper.swift
//  imate
//
//  Created by 天之行 on 2026/5/7.
//

enum LoginHelper {
    static func generateAvatarPrompt(name: String, gender: Int, appearance: String) -> String {
        let genderHint = ["male", "female", ""][gender]
        let components: [String] = [
            "portrait of \(name)",
            genderHint,
            appearance,
            "single, adult, high detail, focus on expression, soft lighting"
        ]
        return components.joined(separator: ",")
    }
}
