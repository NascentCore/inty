//
//  LoginEmailPassword.swift
//  imate
//
//  Created by 天之行 on 2026/4/21.
//

import SwiftUI

import SwiftUI

struct LoginEmailPassword: View {
    
    @EnvironmentObject var router: Router
    
    // 外部传入参数
//    let email: String
//    var onBack: () -> Void
//    var onLogin: (String, String) -> Void
    
    // 内部状态
    @State private var password: String = ""
    @State private var isPasswordVisible: Bool = false
    
    // 颜色常量 (参考 Kotlin 中的 0xFF1C1523 等)
    private let primaryColor = Color(red: 44/255, green: 123/255, blue: 182/255) // 模拟 primary
    private let backgroundColorTop = Color(red: 28/255, green: 21/255, blue: 35/255)
    private let backgroundColorBottom = Color(red: 14/255, green: 11/255, blue: 20/255)

    var body: some View {
        ZStack {
            // 1. 背景层：线性渐变
            LinearGradient(
                gradient: Gradient(colors: [backgroundColorTop, backgroundColorBottom]),
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            // 2. 内容层
            VStack(alignment: .leading, spacing: 0) {
                
                // 返回按钮
                Button(action: {
                    router.pop()
                }) {
                    Image(systemName: "arrow.left")
                        .font(.system(size: 20, weight: .semibold))
                        .foregroundColor(.white)
                        .padding(.vertical, 10)
                }
                
                Spacer().frame(height: 40)

                // 标题
                Text("Login with email password")
                    .font(.title2)
                    .fontWeight(.bold)
                    .foregroundColor(.white)

                Spacer().frame(height: 40)

                // Email 输入框 (禁用状态)
                TextField("", text: .constant("email"))
                    .padding()
                    .background(
                        RoundedRectangle(cornerRadius: 30)
                            .stroke(primaryColor.opacity(0.5), lineWidth: 1)
                    )
                    .foregroundColor(.white.opacity(0.7))
                    .disabled(true)

                Spacer().frame(height: 24)

                // Password 输入框
                HStack {
                    if isPasswordVisible {
                        TextField("Enter password", text: $password)
                    } else {
                        SecureField("Enter password", text: $password)
                    }
                    
                    Button(action: { isPasswordVisible.toggle() }) {
                        Image(systemName: isPasswordVisible ? "eye.slash.fill" : "eye.fill")
                            .foregroundColor(.white.opacity(0.7))
                    }
                }
                .padding()
                .background(
                    RoundedRectangle(cornerRadius: 30)
                        .stroke(primaryColor, lineWidth: 1)
                )
                .foregroundColor(.white)

                Spacer().frame(height: 32)

                // 登录按钮
                Button(action: {
                    if !password.isEmpty {
//                        onLogin(email, password)
                    }
                }) {
                    Text("Login")
                        .font(.headline)
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .frame(height: 56)
                        .background(password.isEmpty ? primaryColor.opacity(0.7) : primaryColor)
                        .cornerRadius(30)
                }
                .disabled(password.isEmpty)

                Spacer()

                // 底部免责声明
                Text("By continuing, you agree to our terms")
                    .font(.caption2)
                    .foregroundColor(.white.opacity(0.35))
                    .frame(maxWidth: .infinity, alignment: .center)
            }
            .padding(.horizontal, 24)
            .padding(.top, 20) // 考虑到系统安全区域
        }
        .navigationBarHidden(true) // 隐藏系统原生导航栏
    }
}
