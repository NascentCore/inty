//
//  LoginInitChatModel.swift
//  imate
//
//  Created by 天之行 on 2026/4/29.
//

import Foundation

struct ChatMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
}
