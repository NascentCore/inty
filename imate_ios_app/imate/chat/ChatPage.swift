//
//  ContentView.swift
//  imate
//
//  Created by 天之行 on 2026/4/18.
//

import SwiftUI

struct ChatPage: View {
    @State private var inputText: String = ""
    @State private var messages: [ChatMessage] = [
        ChatMessage(text: "Hello! How can I help you today?", isUser: false),
        ChatMessage(text: "I want to know more about iMate.", isUser: true)
    ]

    var body: some View {
        VStack(spacing: 0) {
            // 1. 顶部栏
            ChatPageWidgets.ChatTopBar(
                agentName: "iMate AI",
                statusLine: "Online and ready to chat",
                onOpenSettings: { /* 打开设置 */ }
            )

            // 2. 消息列表
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 10) {
                        ForEach(messages) { msg in
                            ChatPageWidgets.ChatMessageBubble(message: msg.text, isUser: msg.isUser)
                                .id(msg.id)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                }
                .onChange(of: messages.count) { _ in
                    withAnimation {
                        proxy.scrollTo(messages.last?.id, anchor: .bottom)
                    }
                }
            }

            // 3. 底部输入栏
            VStack(spacing: 0) {
                Rectangle()
                    .fill(Color.white.opacity(0.05))
                    .frame(height: 1)
                
                HStack(spacing: 8) {
                    TextField("Message...", text: $inputText)
                        .padding(.horizontal, 16)
                        .frame(height: 46)
                        .background(ChatPageWidgets.ChatColors.textFieldBg)
                        .cornerRadius(23)
                        .foregroundColor(.white)
                        .submitLabel(.send)
                        .onSubmit(sendMessage)

                    Button(action: sendMessage) {
                        Image(systemName: "paperplane.fill")
                            .font(.system(size: 18))
                            .foregroundColor(.white)
                            .frame(width: 46, height: 46)
                            .background(ChatPageWidgets.ChatColors.textFieldBg)
                            .clipShape(Circle())
                    }
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 13)
            }
            .background(ChatPageWidgets.ChatColors.background)
        }
        .background(ChatPageWidgets.ChatColors.background.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
    }

    private func sendMessage() {
        guard !inputText.isEmpty else { return }
        let newMsg = ChatMessage(text: inputText, isUser: true)
        messages.append(newMsg)
        inputText = ""
    }
}

// 辅助模型
struct ChatMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
}
