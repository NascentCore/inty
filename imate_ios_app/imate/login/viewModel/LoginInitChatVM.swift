//
//  fwe.swift
//  imate
//
//  Created by 天之行 on 2026/4/28.
//

import Foundation
import SwiftUI
import Combine

enum LoginInitStep: Int, CaseIterable {
    case step1 = 1
    case step2
    case step3
    case step4
    case step5
    
    var topBgColor: Color {
        switch self {
        case .step1: return Color(hex: 0xFF1B152B)
        case .step2: return Color(hex: 0xFF19223E)
        case .step3: return Color(hex: 0xFF172E4F)
        case .step4: return Color(hex: 0xFF15375D)
        case .step5: return Color(hex: 0xFF143C64)
        }
    }
    
    var desc: String? {
        switch self {
        case .step1: return "begining"
        case .step2: return "name confirmed"
        case .step3: return "gender confirmed"
        case .step4: return "personality confirmed"
        case .step5: return "all done"
        }
    }
    
    var progress: Double {
        switch self {
        case .step1: return 0
        case .step2: return 0.2
        case .step3: return 0.4
        case .step4: return 0.8
        case .step5: return 1
        }
    }
}



@MainActor
class LoginInitChatVM: ObservableObject {
    
    @Published var steps: LoginInitStep = .step1
    @Published var messages: [ChatMessage] = [
//        .init(text: LoginConstants.InitChatMsg.step1_1, isUser: false),
//        .init(text: LoginConstants.InitChatMsg.step1_2, isUser: false),
//        .init(text: LoginConstants.InitChatMsg.step1_3, isUser: false),
//        .init(text: LoginConstants.InitChatMsg.step1_4, isUser: false)
    ]
    @Published var progress: Double = 1.0
    @Published var inputText: String = ""
    @Published var selectedGender: String? = nil
    
    init() {
     startConversation()
    }
    
    func startConversation() {
        messages.append(.init(text: LoginConstants.InitChatMsg.step1_1, isUser: false))
        messages.append(.init(text: LoginConstants.InitChatMsg.step1_2, isUser: false))
        messages.append(.init(text: LoginConstants.InitChatMsg.step1_3, isUser: false))
        messages.append(.init(text: LoginConstants.InitChatMsg.step1_4, isUser: false))
    }
    
    func afterNameComfirm() {
        messages.append(.init(text: LoginConstants.InitChatMsg.step2_1, isUser: false))
        messages.append(.init(text: LoginConstants.InitChatMsg.step2_2, isUser: false))
        messages.append(.init(text: LoginConstants.InitChatMsg.step2_3, isUser: false))
    }
    
    func afterGenderComfirm() {
        messages.append(.init(text: LoginConstants.InitChatMsg.step3_1, isUser: false))
        messages.append(.init(text: LoginConstants.InitChatMsg.step3_2, isUser: false))
        messages.append(.init(text: LoginConstants.InitChatMsg.step3_3, isUser: false))
        messages.append(.init(text: LoginConstants.InitChatMsg.step3_4, isUser: false))
    }
    
    func sendMessage() {
        guard !inputText.isEmpty else { return }

        let userMsg = ChatMessage(text: inputText, isUser: true)
        messages.append(userMsg)

        inputText = ""

        // 模拟 AI 回复
        DispatchQueue.main.asyncAfter(deadline: .now() + 1) {
//            self.messages.append(
//                .init(text: "\(userMsg.text)... I love that! ✨", isUser: false)
//            )
            // 进入下一步
            self.nextStep()
        }
    }
    
//    func selectGender(_ gender: String) {
//        selectedGender = gender
//        messages.append(.init(text: gender, isUser: true))
//        messages.append(
//            .init(text: "That is me! I can feel myself becoming real now...", isUser: false)
//        )
//        self.nextStep()
//    }
    
    func nextStep() {
        switch steps {
        case .step1:  // 输入昵称后
            afterNameComfirm()
            steps = .step2
        case .step2:  // 选择性别后
            afterGenderComfirm()
            steps = .step3
        case .step3:
            steps = .step4
            break
            
        case .step4:
            steps = .step5
            break
            
        case .step5:
            break
        }
    }
}
