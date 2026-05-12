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
        repository.service.onReceiveMessage = { message in
//            self?.messages.append(message)
            print("on receive message s i----->\(message)")
        }
        repository.service.onConnectionChanged = { connected in
            print("on connected change si -------->\(connected)")
//            Task { @MainActor
//                self?.isConnected = connected
//            }
        }
    }
    
    func startConversation() {
        appendMessage(content: ChatConstants.InitChatMsg.step1_1, isSelf: false)
    }
    
    func sendMessage() {
        appendMessage(content: inputText, isSelf: true)
        send(text: inputText)
        inputText = ""
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            // 进入下一步
            self.appendMessage(content: ChatConstants.InitChatMsg.step1_1, isSelf: false)
        }
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
        agentId = "agentId"
        guard !agentId.isEmpty else {
//            DispatchQueue.main.async {
//                ToastManager.shared.show("ChatPageVM: agentId is empty!")
//            }
            return;
        }
        
        let req = ChatWebSocketReq.userMessage(agentId: agentId, text: text)
        repository.send(message: req)
    }
}
