//
//  ChatAgent.swift
//  imate
//
//  Created by 天之行 on 2026/5/16.
//


import Foundation

struct ChatAgent: Codable, Identifiable, Equatable {
    let agentId: String
    var name: String
    var avatar: String

    var id: String { agentId }
}
