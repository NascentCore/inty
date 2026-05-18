//
//  IMSettingBottomSheet.swift
//  imate
//
//  Created by 天之行 on 2026/5/18.
//

import SwiftUI

struct IMSettingBottomSheet: View {
    @Binding var isPresented: Bool

    var body: some View {
        GeometryReader { geometry in
            let screenHeight = geometry.size.height
            let sheetHeight = screenHeight * 0.7

            ZStack(alignment: .bottom) {
                // 半透明背景
                Color.black.opacity(0.35)
                    .ignoresSafeArea()
                    .onTapGesture {
                        dismiss()
                    }

                // 底部弹框内容
                VStack(spacing: 0) {
                    // 顶部小横条
                    Capsule()
                        .fill(Color.gray.opacity(0.4))
                        .frame(width: 40, height: 5)
                        .padding(.top, 10)
                        .padding(.bottom, 12)

                    // 标题栏
                    HStack {
                        Text("聊天设置")
                            .font(.headline)

                        Spacer()

                        Button {
                            dismiss()
                        } label: {
                            Image(systemName: "xmark")
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundColor(.gray)
                                .frame(width: 32, height: 32)
                                .background(Color.gray.opacity(0.15))
                                .clipShape(Circle())
                        }
                    }
                    .padding(.horizontal)
                    .padding(.bottom, 12)

                    Divider()

                    // 弹框内部内容
                    VStack(spacing: 0) {
                        settingRow(
                            icon: "bell",
                            title: "消息通知",
                            subtitle: "管理当前聊天通知"
                        )

                        settingRow(
                            icon: "person.crop.circle",
                            title: "用户资料",
                            subtitle: "查看对方资料信息"
                        )

                        settingRow(
                            icon: "photo",
                            title: "聊天背景",
                            subtitle: "设置当前聊天背景"
                        )

                        settingRow(
                            icon: "trash",
                            title: "清空聊天记录",
                            subtitle: "删除本地聊天记录",
                            titleColor: .red
                        )
                    }

                    Spacer()
                }
                .frame(width: geometry.size.width, height: sheetHeight)
                .background(
//                    Color.white
//                        .clipShape(
//                            RoundedCornerShape(
//                                radius: 24,
//                                corners: [.topLeft, .topRight]
//                            )
//                        )
                )
                .ignoresSafeArea(edges: .bottom)
                .transition(.move(edge: .bottom))
            }
        }
    }

    private func dismiss() {
        withAnimation(.spring(response: 0.35, dampingFraction: 0.88)) {
            isPresented = false
        }
    }

    private func settingRow(
        icon: String,
        title: String,
        subtitle: String,
        titleColor: Color = .primary
    ) -> some View {
        HStack(spacing: 14) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(titleColor)
                .frame(width: 32, height: 32)

            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(titleColor)

                Text(subtitle)
                    .font(.system(size: 13))
                    .foregroundColor(.gray)
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(.gray.opacity(0.7))
        }
        .padding(.horizontal)
        .padding(.vertical, 14)
        .contentShape(Rectangle())
    }
}
