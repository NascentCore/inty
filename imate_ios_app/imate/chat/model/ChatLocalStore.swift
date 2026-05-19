//
//  ChatLocalStore.swift
//  imate
//
//  Created by Codex on 2026/5/16.
//

import Foundation

final class ChatLocalStore {

    static let shared = ChatLocalStore()

    private let directoryURL: URL
    private let agentsURL: URL
    private let encoder: JSONEncoder
    private let decoder: JSONDecoder

    init(fileManager: FileManager = .default) {
        let baseURL = fileManager.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? fileManager.temporaryDirectory
        directoryURL = baseURL.appendingPathComponent("iMateLocalChat", isDirectory: true)
        agentsURL = directoryURL.appendingPathComponent("agents.json")

        encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601

        decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
    }

    func upsertAgent(_ agent: ChatAgent) throws {
        try ensureDirectory()
        var agents = try loadAgents()
        agents[agent.agentId] = agent
        let data = try encoder.encode(agents)
        try data.write(to: agentsURL, options: [.atomic])
    }

    func loadAgent(agentId: String) throws -> ChatAgent? {
        try loadAgents()[agentId]
    }

    func loadRecentMessages(agentId: String, limit: Int) throws -> [PersistentChatMessage] {
        let messages = try loadMessages(agentId: agentId)
            .sorted { $0.timestamp < $1.timestamp }

        guard limit > 0, messages.count > limit else {
            return messages
        }

        return Array(messages.suffix(limit))
    }

    func appendMessage(_ message: PersistentChatMessage) throws {
        try ensureDirectory()
        var messages = try loadMessages(agentId: message.agentId)
        messages.append(message)
        messages.sort { $0.timestamp < $1.timestamp }
        let data = try encoder.encode(messages)
        try data.write(to: messagesURL(agentId: message.agentId), options: [.atomic])
    }

    private func loadAgents() throws -> [String: ChatAgent] {
        guard FileManager.default.fileExists(atPath: agentsURL.path) else {
            return [:]
        }

        let data = try Data(contentsOf: agentsURL)
        return try decoder.decode([String: ChatAgent].self, from: data)
    }

    private func loadMessages(agentId: String) throws -> [PersistentChatMessage] {
        let url = messagesURL(agentId: agentId)
        guard FileManager.default.fileExists(atPath: url.path) else {
            return []
        }

        let data = try Data(contentsOf: url)
        return try decoder.decode([PersistentChatMessage].self, from: data)
    }

    private func messagesURL(agentId: String) -> URL {
        let safeAgentId = agentId.addingPercentEncoding(withAllowedCharacters: .alphanumerics) ?? agentId
        return directoryURL.appendingPathComponent("messages-\(safeAgentId).json")
    }

    private func ensureDirectory() throws {
        try FileManager.default.createDirectory(at: directoryURL, withIntermediateDirectories: true)
    }
}
