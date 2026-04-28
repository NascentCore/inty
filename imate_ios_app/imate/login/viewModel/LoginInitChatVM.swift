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
    
    var topBgColor: Color {
        switch self {
        case .step1: return Color.red
        case .step2: return Color.blue
        case .step3: return Color.yellow
        }
    }
    
//    var buttonTitle: String {
//        switch self {
//        case .step1: return "下一步"
//        case .step2: return "验证"
//        case .step3: return "完成"
//        }
//    }
}

@MainActor
class LoginInitChatVM: ObservableObject {
    
    @Published var steps: LoginInitStep = .step1
    
    func nextStep() {
          switch steps {
          case .step1:
              steps = .step2
          case .step2:
              steps = .step3
          case .step3:
              break
          }
      }
}
