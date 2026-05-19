//
//  PersistentChatMessage.swift
//  imate
//
//  Created by Codex on 2026/5/16.
//

import Foundation

struct PersistentChatMessage: Codable, Identifiable, Equatable {
    let messageId: String
    let agentId: String
    let content: String
    let isBot: Bool
    let timestamp: Date

    var id: String { messageId }
}
