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
//    static let divider = Color(white: 0.15)
}

struct LoginInitChat: View {
    @EnvironmentObject var router: Router
    @StateObject var vm = LoginInitChatVM()
    
    var body: some View {
        ZStack() {
            LoginInitChatWidgets.background
            
            VStack(spacing: 0) {
                // 1. 顶部
                LoginInitChatWidgets.Header(
                    progress: vm.steps.progress,
                    bgColor: vm.steps.topBgColor,
                    name: vm.name
                )
                
                // 2. 聊天列表
                LoginInitChatWidgets.ChatList(messages: vm.messages)

                // 3. 底部输入栏
                if vm.steps == .step2 {
                    LoginInitChatWidgets.GenderSelectBottom(
                        onSelect: vm.selectGender(i:)
                    )
                } else if vm.steps == .step5 {
                    LoginInitChatWidgets.ButtonFinish(onFinish: goChat)
                } else {
                    Divider()
                    LoginInitChatWidgets.InputBar(
                        inputText: $vm.inputText,
                        onSend: vm.sendMessage,
                        hint: vm.steps.inputHint
                    )
                }
            }
            
            
        }
        .background(Color.black.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
        .task {
            vm.startConversation()
        }
    }
    
    private func goChat() {
        router.push(.chatPage)
    }
}

#Preview {
    LoginInitChat()
}

