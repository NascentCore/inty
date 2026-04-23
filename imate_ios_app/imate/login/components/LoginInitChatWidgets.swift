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
    
    
}
