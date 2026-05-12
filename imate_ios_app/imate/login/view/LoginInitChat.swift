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
    @StateObject var userManager = UserManager.shared
    
    var body: some View {
        ZStack() {
            LoginInitChatWidgets.background
            
            VStack(spacing: 0) {
                // 1. 顶部
                LoginInitChatWidgets.Header(
                    progress: vm.steps.progress,
                    bgColor: vm.steps.topBgColor,
                    name: vm.name,
                    avatar: userManager.avatar
                )
                
                // 2. 聊天列表
                LoginInitChatWidgets.ChatList(messages: vm.messages)

                // 3. 底部输入栏
                if vm.steps == .step2 {
                    LoginInitChatWidgets.GenderSelectBottom(
                        onSelect: vm.selectGender(i:)
                    )
                } else if vm.steps == .step4 {
                    Divider()
                    LoginInitChatWidgets.GenerateAvatarLoading()
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
            
            // 测试代码
//            userManager.avatar = "https://images.sxwl.dev/inty-static/backgrounds/user-01KPAHMNWP635JRYAWYGDS3PRS/0359f9d22890466e8ccc0b21823dc98e/1778164707078/sample_0.jpg"
        }
    }
    
    private func goChat() {
        Task {
            await vm.createAgent()
        }
        router.push(.chatPage)
    }
}

#Preview {
    LoginInitChat()
}

