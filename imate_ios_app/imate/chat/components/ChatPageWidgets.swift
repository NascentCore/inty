//
//  ChatPageWidgets.swift
//  imate
//
//  Created by 天之行 on 2026/4/24.
//
import SwiftUI

enum ChatPageWidgets {
    
    struct ChatColors {
        static let background = Color(hex: 0xFF1C1523)
        static let topBarGradient = [Color(hex: 0x1E2A38).opacity(0.95), Color(hex: 0x1C1523).opacity(0)]
        static let userBubbleStart = Color(hex: 0x2C7BB6)
        static let userBubbleEnd = Color(hex: 0x5BA3D4)
        static let agentBubbleBg = Color(red: 43/255, green: 39/255, blue: 51/255) // 模拟 AgentBubbleBackground
        static let agentBubbleBorder = Color(white: 0.2)
        static let textFieldBg = Color(hex: 0x25202B) // 模拟 TextFieldBackground
    }
    
    struct ChatMessageBubble: View {
        let message: String
        let isUser: Bool

        var body: some View {
            HStack {
                if isUser { Spacer() }
                
                Text(message)
                    .font(.system(size: 14))
                    .lineSpacing(6)
                    .foregroundColor(.white)
                    .padding(.horizontal, 15)
                    .padding(.vertical, 11)
                    .background(bubbleBackground)
                    .clipShape(bubbleShape)
                    .shadow(color: isUser ? ChatColors.userBubbleStart.opacity(0.3) : Color.black.opacity(0.2), radius: 8, x: 0, y: 4)
                
                if !isUser { Spacer() }
            }
        }

        private var bubbleShape: some Shape {
            if isUser {
                // 用户气泡：右下角小圆角
                return AnyShape(RoundedRectangle(cornerRadius: 18)
                    .path(in: CGRect(x: 0, y: 0, width: 271, height: 100))) // 简化演示，实际应使用 Custom Shape
            } else {
                return AnyShape(RoundedRectangle(cornerRadius: 18))
            }
        }

        @ViewBuilder
        private var bubbleBackground: some View {
            if isUser {
                LinearGradient(
                    colors: [ChatColors.userBubbleStart, ChatColors.userBubbleEnd],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            } else {
                ChatColors.agentBubbleBg
                    .overlay(RoundedRectangle(cornerRadius: 18).stroke(ChatColors.agentBubbleBorder, lineWidth: 1))
            }
        }
    }
    
    struct ChatTopBar: View {
        let agentName: String
        let statusLine: String
        var onOpenSettings: () -> Void

        var body: some View {
            HStack(spacing: 12) {
                // 头像部分
                ZStack {
                    Circle()
                        .stroke(Color(hex: 0xFF88B3).opacity(0.55), lineWidth: 2)
                        .frame(width: 40, height: 40)
                    
                    Image(systemName: "person.circle.fill") // 占位符
                        .resizable()
                        .frame(width: 36, height: 36)
                        .clipShape(Circle())
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text(agentName)
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(.white)
                    
                    if !statusLine.isEmpty {
                        Text(statusLine)
                            .font(.system(size: 11))
                            .foregroundColor(.white.opacity(0.45))
                            .lineLimit(1)
                    }
                }
                
                Spacer()

                // 设置按钮
                Button(action: onOpenSettings) {
                    Image(systemName: "gearshape")
                        .font(.system(size: 17))
                        .foregroundColor(.white)
                        .frame(width: 38, height: 38)
                        .background(ChatColors.textFieldBg)
                        .clipShape(Circle())
                        .overlay(Circle().stroke(Color.white.opacity(0.1), lineWidth: 1))
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(
                LinearGradient(colors: ChatColors.topBarGradient, startPoint: .top, endPoint: .bottom)
            )
        }
    }
    
    
}
