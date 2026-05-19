//
//  GlobalToastOverlay.swift
//  imate
//
//  Created by 天之行 on 2026/4/27.
//

import SwiftUI

struct GlobalToastOverlay: View {
    // 核心点：必须使用 @ObservedObject 监听单例
    @ObservedObject var manager = ToastManager.shared

    var body: some View {
        ZStack {
            if manager.isShowing {
                // 半透明背景（可选）：防止 Toast 显示时背景颜色太杂乱
                Text(manager.message)
                    .font(.system(size: 16, weight: .medium))
                    .foregroundColor(.white)
                    .padding(.horizontal, 24)
                    .padding(.vertical, 12)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(manager.type.color.opacity(0.8))
                    )
                    .shadow(color: .black.opacity(0.2), radius: 10)
                    .transition(.scale(scale: 0.8).combined(with: .opacity)) // 居中通常配合缩放动画
                    .zIndex(999)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity) // 关键：撑满屏幕，否则 ZStack 找不到中心
        .ignoresSafeArea() // 忽略安全区域，确保真正居中
        .allowsHitTesting(false) // 穿透点击，不影响下方按钮
    }
}
