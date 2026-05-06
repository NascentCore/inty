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
    
    var inputHint: String {
        switch self {
        case .step1: return LoginConstants.InitChatMsg.stepHintName
        case .step3: return LoginConstants.InitChatMsg.stepHintDesc
        default: return "input..."
        }
    }
}



@MainActor
class LoginInitChatVM: ObservableObject {
    
    @Published var steps: LoginInitStep = .step1
    @Published var messages: [ChatMessage] = []
    @Published var progress: Double = 1.0
    @Published var inputText: String = ""
    @Published var selectedGender: String? = nil
    
    @Published var name: String = "iMate"
    @Published var gender: Int = -1  // -1 not set, 0 male, 1 female, 2 no prof
    
    init() {
//     startConversation()
    }
    
    func startConversation() {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) {
            self.appendMessage(content: LoginConstants.InitChatMsg.step1_1, isSelf: false)
            self.appendMessage(content: LoginConstants.InitChatMsg.step1_2, isSelf: false)
            self.appendMessage(content: LoginConstants.InitChatMsg.step1_3, isSelf: false)
        }
    }
    
    func afterNameComfirm() {
        let content = "\(LoginConstants.InitChatMsg.step2_1) \(name) \(LoginConstants.InitChatMsg.step2_2)"
        appendMessage(content: content, isSelf: false)
        appendMessage(content: LoginConstants.InitChatMsg.step2_3, isSelf: false)
    }
    
    func sendMessage() {
        guard !inputText.isEmpty else { return }
        if steps == .step1 {
            setName()
        } else if steps == .step3 {
            inputAppearance()
        }
    }
    
    func setName() {
        name = inputText
        appendMessage(content: inputText, isSelf: true)
        inputText = ""
//        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
//            self.nextStep()
//        }
        nextStep()
    }
    
    func selectGender(i: Int) {
        gender = i
        let s = ["Male ❤️", "Female ❤️", "No Prof ❤️"][i]
        appendMessage(content: s, isSelf: true)
        appendMessage(content: LoginConstants.InitChatMsg.step3_1, isSelf: false)
        appendMessage(content: LoginConstants.InitChatMsg.step3_2, isSelf: false)
        appendMessage(content: LoginConstants.InitChatMsg.step3_3, isSelf: false)
        nextStep()
    }
    
    func inputAppearance() {
        appendMessage(content: inputText, isSelf: true)
        let s = "\(inputText)\(LoginConstants.InitChatMsg.step4_1)"
        appendMessage(content: s, isSelf: false)
        inputText = ""
        
        nextStep()
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            let content = "\(LoginConstants.InitChatMsg.step5_1)\(self.name)! \(LoginConstants.InitChatMsg.step5_2)"
            self.appendMessage(content: content, isSelf: false)
            self.appendMessage(content: LoginConstants.InitChatMsg.step5_3, isSelf: false)
            self.nextStep()
        }
    }
    
    func nextStep() {
        switch steps {
        case .step1:  // 输入昵称后
            afterNameComfirm()
            steps = .step2
            break
            
        case .step2:  // 选择性别后
            steps = .step3
            break
            
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
    
    func appendMessage(content: String, isSelf: Bool) {
        withAnimation(.spring(response: 0.3, dampingFraction: 0.75)) {
            messages.append(.init(text: content, isUser: isSelf))
        }
    }
}
