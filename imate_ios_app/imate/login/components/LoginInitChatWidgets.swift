//
//  LoginInitChatWidgets.swift
//  imate
//
//  Created by 天之行 on 2026/4/23.
//

import SwiftUI

enum LoginInitChatWidgets {
    
    // 聊天起泡
    struct InitChatBubble: View {
        let message: String
        let isAgent: Bool
        @State private var revealed = false

        var body: some View {
            HStack {
                if !isAgent { Spacer() }
                
                Text(message)
                    .font(.system(size: 14))
                    .lineSpacing(4)
                    .foregroundColor(.white)
                    .padding(.horizontal, 17)
                    .padding(.vertical, 13)
                    .background(bubbleBackground)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
                    .opacity(revealed ? 1 : 0)
                    .offset(y: revealed ? 0 : 14)
                
                if isAgent { Spacer() }
            }
            .onAppear {
                withAnimation(.easeOut(duration: 0.32)) {
                    revealed = true
                }
            }
        }

        @ViewBuilder
        private var bubbleBackground: some View {
            if isAgent {
                RoundedRectangle(cornerRadius: 18)
                    .fill(InitChatColors.agentBubbleBg)
                    .overlay(RoundedRectangle(cornerRadius: 18).stroke(InitChatColors.agentBubbleBorder, lineWidth: 1))
            } else {
                LinearGradient(
                    colors: [InitChatColors.userBubbleStart, InitChatColors.userBubbleEnd],
                    startPoint: .leading,
                    endPoint: .trailing
                )
            }
        }
    }
    
    // 顶部Header 与进度条
    struct InitChatHeader: View {
        let progress: Double
        let title: String
        let subtitle: String
        let avatarUrl: String?

        var body: some View {
            VStack(spacing: 12) {
                // 用户信息行
                HStack(spacing: 12) {
                    Circle() // 简化版头像
                        .fill(InitChatColors.userBubbleStart)
                        .frame(width: 44, height: 44)
                        .overlay(Circle().stroke(InitChatColors.userBubbleStart.opacity(0.5), lineWidth: 2))
                    
                    VStack(alignment: .leading, spacing: 2) {
                        Text(title).font(.system(size: 16, weight: .bold)).foregroundColor(.white)
                        Text(subtitle).font(.system(size: 11)).foregroundColor(.white.opacity(0.5))
                    }
                    Spacer()
                }

                // 完成度标签
                HStack {
                    Text("PROFILE COMPLETION").font(.system(size: 11)).foregroundColor(.white.opacity(0.5))
                    Spacer()
                    Text("\(Int(progress * 100))%").font(.system(size: 12, weight: .semibold)).foregroundColor(InitChatColors.userBubbleEnd)
                }

                // 进度条
                ZStack(alignment: .leading) {
                    Capsule().fill(InitChatColors.progressTrack).frame(height: 4)
                    Capsule()
                        .fill(LinearGradient(colors: [InitChatColors.userBubbleStart, InitChatColors.userBubbleEnd, Color(hex: 0xC3F0FD)], startPoint: .leading, endPoint: .trailing))
                        .frame(width: UIScreen.main.bounds.width * CGFloat(progress), height: 4)
                        .animation(.spring(), value: progress)
                }
            }
            .padding()
            .background(InitChatColors.headerBg)
        }
    }
    
    // 背景渐变色
    static var background: some View {
        LinearGradient(
            colors: [
//                Color.black,
//                Color.purple.opacity(0.8),
//                Color.blue.opacity(0.6)
                Color(hex: 0xFF1C1523),
                Color(hex: 0xFF1C1523)
            ],
            startPoint: .bottom,
            endPoint: .top
        )
        .ignoresSafeArea()
    }
    
    struct Header: View {
        let progress: Double
        let bgColor: Color
        
        var body: some View {
            VStack(alignment: .leading, spacing: 12) {

                HStack {
                    Circle()
                        .fill(Color.gray)
                        .frame(width: 40, height: 40)

                    VStack(alignment: .leading) {
                        Text("Marin")
                            .foregroundColor(.white)
                            .bold()

                        Text("Ready! ✨")
                            .foregroundColor(.white.opacity(0.7))
                            .font(.caption)
                    }

                    Spacer()
                }

                ProgressView(value: progress)
                    .tint(.purple)
            }
            .padding()
            .background(bgColor)
        }
    }
    
    
    // 聊天列表
    struct ChatList: View {
        let messages: [ChatMessage]
        
        var body: some View {
            ScrollViewReader { proxy in
                ScrollView {
                    VStack(spacing: 12) {
                        ForEach(messages) { msg in
                            ChatBubble(message: msg)
                                .id(msg.id)
                        }
                    }
                    .padding()
                }
                .onChange(of: messages.count) { _ in
                    if let last = messages.last {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
        }
    }
    
    
    // 聊天气泡
    struct ChatBubble: View {
        let message: ChatMessage
        
        var body: some View {
            HStack {
                if message.isUser { Spacer() }

                Text(message.text)
                    .padding()
                    .background(message.isUser ? Color.purple : Color.gray.opacity(0.3))
                    .foregroundColor(.white)
                    .cornerRadius(16)

                if !message.isUser { Spacer() }
            }
        }
    }
    
    
    // 输入框
    struct InputBar: View {
        @Binding var inputText: String
        let onSend: () -> Void
        
        var body: some View {
            HStack {
                TextField("Type...", text: $inputText)
                    .padding()
                    .background(Color.white.opacity(0.1))
                    .frame(height: 46)
                    .cornerRadius(23)
                    .foregroundColor(.white)
//
//                Button("Send") {
//                    onSend()
//                }
                Button(action: onSend) {
                    Image(systemName: "paperplane.fill")
                        .foregroundColor(.white)
                        .frame(width: 46, height: 46)
                        .background(InitChatColors.textFieldBg)
                        .clipShape(Circle())
                }
            }
            .padding()
        }
    }
    
    
}
