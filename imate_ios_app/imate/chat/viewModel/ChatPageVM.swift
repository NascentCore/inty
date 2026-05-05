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
    init() {
     startConversation()
    }
    
    func startConversation() {
        appendMessage(content: ChatConstants.InitChatMsg.step1_1, isSelf: false)
    }
    
    func sendMessage() {
        appendMessage(content: inputText, isSelf: true)
        inputText = ""
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
            // 进入下一步
            self.appendMessage(content: ChatConstants.InitChatMsg.step1_1, isSelf: false)
        }
    }
    
    
    func appendMessage(content: String, isSelf: Bool) {
        messages.append(.init(text: content, isUser: isSelf))
    }
}
