//
//  ToastManager.swift
//  imate
//
//  Created by 天之行 on 2026/4/27.
//

import SwiftUI
import Combine

import SwiftUI

class ToastManager: ObservableObject {
    static let shared = ToastManager()
    
    @Published var isShowing: Bool = false
    @Published var message: String = ""
    @Published var type: ToastType = .info
    
    enum ToastType {
        case info, success, error
        
        var color: Color {
            switch self {
            case .info: return .gray
            case .success: return .green
            case .error: return .red
            }
        }
    }
    
    // 用于存储当前正在倒计时的任务
    private var pendingWorkItem: DispatchWorkItem?

    @MainActor
    func show(_ message: String, duration: TimeInterval = 3.0, type: ToastType = .info) {
        // 1. 立即取消之前的计时任务
        pendingWorkItem?.cancel()
        
        // 2. 更新内容并显示
        self.message = message
        self.type = type
        
        // 如果当前已经在显示，则不需要再次触发动画，直接更新文字即可
        if !isShowing {
            withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
                self.isShowing = true
            }
        }
        
        // 3. 创建新的计时任务
        let task = DispatchWorkItem { [weak self] in
            withAnimation(.easeInOut(duration: 0.5)) {
                self?.isShowing = false
            }
        }
        
        // 4. 保存并执行
        self.pendingWorkItem = task
        DispatchQueue.main.asyncAfter(deadline: .now() + duration, execute: task)
    }
}
