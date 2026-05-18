//
//  ChatSettingsSheet.swift
//  imate
//
//  Created by 天之行 on 2026/5/5.
//

import SwiftUI

struct ChatSettingsSheet: View {
    @Binding var show: Bool

    var body: some View {
        VStack(spacing: 0) {

            // 顶部拖拽条
            Capsule()
                .frame(width: 40, height: 5)
                .foregroundColor(.gray.opacity(0.5))
                .padding(.top, 8)

            // 标题 + 关闭按钮
            HStack {
                Text("Settings")
                    .font(.headline)
                    .foregroundColor(.white)

                Spacer()

                Button {
                    withAnimation {
                        show = false
                    }
                } label: {
                    Image(systemName: "xmark")
                        .padding(8)
                        .background(Color.gray.opacity(0.2))
                        .clipShape(Circle())
                }
            }
            .padding()

            Divider()

            // 内容区域（你可以随便换）
            VStack(spacing: 20) {
                Text("Send Feedback").foregroundColor(.white)
                Text("Report an Issue").foregroundColor(.white)
                Text("Terms of Use").foregroundColor(.white)
                Text("Privacy Policy").foregroundColor(.white)

                Divider()

                Text("Logout")
                    .foregroundColor(.white)

                Text("Delete Account")
                    .foregroundColor(.red)
            }
            .padding()

            Spacer()
        }
        .frame(maxWidth: .infinity)
        .frame(height: 500) // 👈 控制高度
        .background(ChatPageWidgets.ChatColors.background)
        .cornerRadius(20)
        .shadow(radius: 10)
        .ignoresSafeArea(edges: .bottom)
    }
}
