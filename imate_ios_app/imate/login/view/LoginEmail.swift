//
//  EmailInput.swift
//  imate
//
//  Created by 天之行 on 2026/4/20.
//

import SwiftUI

struct LoginEmail: View {
    // 状态管理
    @State private var emailError: String? = nil
    @FocusState private var isTextFieldFocused: Bool // 自动聚焦控制
    
    @EnvironmentObject var router: Router
    @EnvironmentObject var userManager: UserManager
    
    // 颜色配置
    private let backgroundGradient = LinearGradient(
        stops: [
            .init(color: Color(hex: 0x1C1523), location: 0),
            .init(color: Color(hex: 0x0E0B14), location: 1)
        ],
        startPoint: .top,
        endPoint: .bottom
    )
    
    var body: some View {
        ZStack {
            // 1. 背景渐变
            LoginWidgets.HeaderBg()
            
            VStack(alignment: .leading, spacing: 0) {
                // 2. 返回按钮
                Button(action: {
                    router.pop()
                }) {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 20, weight: .medium))
                        .foregroundColor(.white)
                        .frame(width: 44, height: 44)
                }
                .padding(.leading, 12)
                .padding(.top, 0)
                
                VStack(alignment: .leading, spacing: 40) {
                    // 3. 标题
                    Text("Email")
                        .font(.title2)
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                        .padding(.top, 20)
                    
                    VStack(alignment: .leading, spacing: 8) {
                        // 4. 输入框 (OutlinedTextField 风格)
                        TextField("", text: $userManager.email, prompt:
                            Text("Enter your Email")
                                .foregroundColor(.white.opacity(0.5)) // alpha = 0.5f
                        )
                        .focused($isTextFieldFocused)
                        .keyboardType(.emailAddress)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                        .foregroundColor(.white)
                        .padding(.horizontal, 20)
                        .frame(height: 56)
                        .background(
                            RoundedRectangle(cornerRadius: 30)
                                .stroke(emailError != nil ? Color.red : Color.purple, lineWidth: 1) // 对应 primary 颜色
                        )
                        .onChange(of: userManager.email) { _ in
                            if userManager.email.count > 50 { userManager.email = String(userManager.email.prefix(50)) }
                            emailError = nil
                        }
                        
                        // 5. 错误提示
                        if let error = emailError {
                            Text(error)
                                .font(.caption)
                                .foregroundColor(.red)
                                .padding(.leading, 16)
                        }
                    }
                    
                    // 6. 继续按钮
                    Button(action: handleContinue) {
                        Text("Continue")
                            .font(.headline)
                            .fontWeight(.semibold)
                            .foregroundColor(.white)
                            .frame(maxWidth: .infinity)
                            .frame(height: 56)
                            .background(Color.purple) // 对应 primary
                            .cornerRadius(30)
                    }
                }
                .padding(.horizontal, 24)
                
                Spacer()
                
                // 7. 免责声明 (对应底部的 login_disclaimer)
                Text("By continuing, you agree to our Terms and Conditions.")
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.35)) // alpha = 0.35f
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                    .padding(.bottom, 20)
            }
        }
        .navigationBarHidden(true)
    }
    
    // 验证逻辑
    private func handleContinue() {
        if userManager.email.trimmingCharacters(in: .whitespaces).isEmpty || !ToolHelper.isValidEmail(userManager.email) {
            emailError = "Invalid email format"
        } else {
//            print("on Emai err is---->\(userManager.email)")
            router.push(.loginEmailPassword)
        }
    }
    
    
}
