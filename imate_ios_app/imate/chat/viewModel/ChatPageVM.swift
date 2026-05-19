//
//  ChatPageVM.swift
//  imate
//
//  Created by 天之行 on 2026/5/5.
//

import Combine
import Foundation

@MainActor
class ChatPageVM: ObservableObject {
    
    @Published var messages: [ChatMessage] = []
    @Published var inputText: String = ""
    
    @Published var showSettings: Bool = false
    
    @Published var isConnected = false
    @Published var agent: ChatAgent
    
    var agentId: String = ""
    private let repository = ChatRepository.shared
    
    init() {
        let fallbackAgent = ChatRepository.demoAgent
        agentId = UserManager.shared.agentId ?? ""
        agent = ChatAgent(agentId: agentId, name: "IMATE", avatar: "")
        loadRecentMessages(agentId: agentId)
        
        repository.service.onReceiveMessage = { [weak self] message in
            let msg = ChatMessage(text: message.choices[0].message.content, isUser: false, isBot: false)
            self?.messages.append(msg)
            self?.saveMessageToLocal(content: msg.text, isBot: true)
        }
        repository.service.onConnectionChanged = { [weak self] connected in
            self?.isConnected = connected
        }
    }
    
    func startConversation() {
        appendMessage(content: ChatConstants.InitChatMsg.step1_1, isSelf: false)
    }
    
    func sendMessage() {
        appendMessage(content: inputText, isSelf: true)
        saveMessageToLocal(content: inputText, isBot: false)
        send(text: inputText)
        inputText = ""
    }
    
    
    func appendMessage(content: String, isSelf: Bool) {
        messages.append(.init(text: content, isUser: isSelf, isBot: !isSelf))
    }
    
    // websocket about
    func connect() {
        repository.connect()
    }

    func disconnect() {
        repository.disconnect()
    }

    func send(text: String) {
        guard !agentId.isEmpty else {
            ToastManager.shared.show("ChatPageVM: agentId is empty!")
            return;
        }
        
        let req = ChatWebSocketReq.userMessage(agentId: agentId, text: text)
        repository.send(message: req)
    }
    
    // get message list about
    func loadRecentMessages(agentId: String) {
        do {
            try repository.prepareAgent(agent)
            let recentMessages = try repository.loadRecentMessages(agentId: agentId)
            print("on rrecent message len si -------->\(recentMessages.count)")
            if recentMessages.isEmpty {
                appendMessage(content: ChatConstants.InitChatMsg.step1_1, isSelf: false)
            } else {
                for item in recentMessages {
                    messages.append(.init(text: item.content, isUser: !item.isBot, isBot: item.isBot))
                }
            }
        } catch {
            ToastManager.shared.show("Load chat history failed", duration: 5, type: .error)
        }
    }
    
    func saveMessageToLocal(content: String, isBot: Bool) {
        do {
            try repository.prepareAgent(agent)
            try repository.appendMessage(agentId: agentId, content: content, isBot: isBot)
        } catch {
            ToastManager.shared.show("save chat history failed", duration: 5, type: .error)
        }
    }
}
