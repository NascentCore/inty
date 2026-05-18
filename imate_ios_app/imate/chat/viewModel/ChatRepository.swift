//
//  ChatRepository.swift
//  imate
//
//  Created by Codex on 2026/5/16.
//

import Foundation

final class ChatRepository {

    static let shared = ChatRepository()

    static let demoAgent = ChatAgent(
        agentId: "agent-demo-001",
        name: "iMate AI",
        avatar: ""
    )

    private let localStore: ChatLocalStore

    init(localStore: ChatLocalStore = .shared) {
        self.localStore = localStore
    }

    func prepareAgent(_ agent: ChatAgent) throws {
        try localStore.upsertAgent(agent)
    }

    func loadAgent(agentId: String) throws -> ChatAgent? {
        try localStore.loadAgent(agentId: agentId)
    }

    func loadRecentMessages(agentId: String, limit: Int = 30) throws -> [PersistentChatMessage] {
        try localStore.loadRecentMessages(agentId: agentId, limit: limit)
    }

    @discardableResult
    func appendMessage(
        agentId: String,
        content: String,
        isBot: Bool,
        messageId: String = UUID().uuidString,
        timestamp: Date = Date()
    ) throws -> PersistentChatMessage {
        let message = PersistentChatMessage(
            messageId: messageId,
            agentId: agentId,
            content: content,
            isBot: isBot,
            timestamp: timestamp
        )
        try localStore.appendMessage(message)
        return message
    }
    
    
    // websocket connect、disconnect、send
    let service = ChatWebSocketService()

    func connect() {
        service.connect()
    }

    func disconnect() {
        service.disconnect()
    }

    func send(message: ChatWebSocketReq) {
        service.send(message: message)
    }
}
