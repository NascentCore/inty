//
//  LoginInitChat.swift
//  imate
//
//  Created by 天之行 on 2026/4/23.
//

import SwiftUI

struct InitChatColors {
    static let headerBg = Color(hex: 0x1C1523)
    static let userBubbleStart = Color(hex: 0x2C7BB6)
    static let userBubbleEnd = Color(hex: 0x5BA3D4)
    static let agentBubbleBg = Color(white: 0.15)
    static let agentBubbleBorder = Color(white: 0.2)
    static let progressTrack = Color(white: 0.1)
    static let textFieldBg = Color(white: 0.12)
    static let divider = Color(white: 0.15)
}

struct LoginInitChat: View {
    @State private var messages: [String] = ["Hello! I'm your AI companion.", "What's your name?"]
    @State private var inputText: String = ""
    @State private var progress: Double = 0.2
    
    var body: some View {
        VStack(spacing: 0) {
            // 1. 顶部
            LoginInitChatWidgets.InitChatHeader(
                progress: progress,
                title: "iMate Personalization",
                subtitle: "Building your companion...",
                avatarUrl: nil
            )

            // 2. 聊天列表
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(0..<messages.count, id: \.self) { index in
                            LoginInitChatWidgets.InitChatBubble(message: messages[index], isAgent: index % 2 == 0)
                        }
                    }
                    .padding()
                }
            }

            // 3. 底部输入栏
            VStack {
                Divider().background(InitChatColors.divider)
                
                HStack(spacing: 8) {
                    TextField("Enter your name...", text: $inputText)
                        .padding(.horizontal, 16)
                        .frame(height: 46)
                        .background(InitChatColors.textFieldBg)
                        .cornerRadius(23)
                        .foregroundColor(.white)
                    
                    Button(action: sendMessage) {
                        Image(systemName: "paperplane.fill")
                            .foregroundColor(.white)
                            .frame(width: 46, height: 46)
                            .background(InitChatColors.textFieldBg)
                            .clipShape(Circle())
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 13)
            }
            .background(Color.black)
        }
        .background(Color.black.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
    }

    private func sendMessage() {
        guard !inputText.isEmpty else { return }
        messages.append(inputText)
        inputText = ""
        progress += 0.2 // 模拟进度增加
    }
}
