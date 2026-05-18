//
//  ContentView.swift
//  imate
//
//  Created by 天之行 on 2026/4/18.
//

import SwiftUI

struct ChatPage: View {
    @StateObject  var vm = ChatPageVM()

    var body: some View {
        ZStack(alignment: .bottom) {
            VStack(spacing: 0) {
                // 1. 顶部栏
                ChatPageWidgets.ChatTopBar(
                    agentName: "iMate AI",
                    statusLine: "Online and ready to chat",
                    onOpenSettings: {
                        vm.showSettings = true
                    }
                )

                // 2. 消息列表
                LoginInitChatWidgets.ChatList(messages: vm.messages)

                // 3. 底部输入栏
                Divider()
                    .frame(width: 2)
                LoginInitChatWidgets.InputBar(
                    inputText: $vm.inputText,
                    onSend: vm.sendMessage,
                    hint: "Message Target..."
                )
            }
            
            // 遮罩 + 弹窗
            if vm.showSettings {
                IMSettingBottomSheet(
                    isPresented: $vm.showSettings
                  )
                  .transition(.opacity)
                  .zIndex(10)
                
//                Color.black.opacity(0.4)
//                    .ignoresSafeArea()
//                    .onTapGesture {
//                        withAnimation {
//                            vm.showSettings = false
//                        }
//                    }
//
//                ChatSettingsSheet(show: $vm.showSettings)
//                    .transition(.move(edge: .bottom))
//                    .ignoresSafeArea(edges: .bottom)
            }
        }
        .background(ChatPageWidgets.ChatColors.background.ignoresSafeArea())
        .navigationBarBackButtonHidden(true)
        .onAppear {
            vm.connect()
        }
        .onDisappear {
            vm.disconnect()
        }
    }
}

#Preview {
    ChatPage()
}
