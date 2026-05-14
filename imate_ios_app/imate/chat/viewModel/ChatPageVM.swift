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
    
    var agentId: String = ""
    private let repository = ChatRepository()
    
    init() {
        agentId = UserManager.shared.agentId ?? ""
        repository.service.onReceiveMessage = { [weak self] message in
            let msg = ChatMessage(text: message.choices[0].message.content, isUser: false)
            self?.messages.append(msg)
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
        send(text: inputText)
        inputText = ""
//        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
//            self.appendMessage(content: ChatConstants.InitChatMsg.step1_1, isSelf: false)
//        }
    }
    
    
    func appendMessage(content: String, isSelf: Bool) {
        messages.append(.init(text: content, isUser: isSelf))
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
}
