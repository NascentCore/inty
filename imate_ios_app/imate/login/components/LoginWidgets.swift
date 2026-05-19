//
//  LoginWidgets.swift
//  imate
//
//  Created by 天之行 on 2026/4/19.
//

import SwiftUI

enum LoginWidgets {
    
    // 顶部背景
    struct HeaderBg: View {
        var body: some View {
            LinearGradient(
                gradient: Gradient(colors: [
                    Color(hex: 0xFF1C1523), Color(hex: 0xFF0E0B14)
                ]),
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()
        }
    }
    
    // 顶部icon + iMate 文案
    struct IconAbout: View {
        var body: some View {
            
            VStack(spacing: 20) {
                // 这里模拟图标，实际开发中请替换为您的 Image("logo_name")
                Image("logo")
                    .resizable()
                    .frame(width: 120, height: 120)
                    .clipShape(RoundedRectangle(cornerRadius: 60))
                
                Text("iMate")
                    .font(.system(size: 36, weight: .bold))
                    .foregroundColor(.white)
                
                Text("Your AI, your way")
                    .font(.subheadline)
                    .foregroundColor(.gray)
            }
        }
    }
    
    // Meet 相关文案
    struct DescView: View {
        var body: some View {
            // --- 中间介绍卡片 ---
            VStack {
                Text("Meet your personalized AI companion —\nbuilt around ")
                    .foregroundColor(.gray)
                    .font(.system(size: 16)) +
                Text("you")
                    .foregroundColor(.blue)
                    .fontWeight(.semibold)
                    .font(.system(size: 16)) +
                Text(", growing with every\nconversation.")
                    .foregroundColor(.gray)
                    .font(.system(size: 16))
            }
            .multilineTextAlignment(.center)
            .lineSpacing(4)
            .padding(.horizontal, 20)
            .padding(.vertical, 20)
            .background(
                RoundedRectangle(cornerRadius: 30)
                    .fill(Color(white: 0.12))
            )
            .padding(.horizontal, 20)
        }
    }
    
    // 按钮部分
    struct ButtonView: View {
        var onAppleAction: () -> Void
        var onEmailAction: () -> Void
        
        var body: some View {
            // --- 按钮区域 ---
            VStack(spacing: 20) {
                // Google 登录按钮
                Button(action: {
                    onAppleAction()
                }) {
                    HStack {
                        Image(systemName: "g.circle.fill") // 模拟 Google 图标
                            .font(.title3)
                        Text("Continue with Apple")
                            .fontWeight(.semibold)
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 60)
                    .background(Color.blue.opacity(0.8))
                    .foregroundColor(.white)
                    .cornerRadius(30)
                }

                // 邮箱登录链接
                Button("Continue with Email") {
                    onEmailAction()
                }
                .font(.subheadline)
                .foregroundColor(Color.white.opacity(0.35))
                .underline()
            }
            .padding(.horizontal, 30)
        }
    }
    
    // 底部条款
    struct TermsView: View {
        var body: some View {
            // --- 底部条款 ---
            HStack(spacing: 15) {
                Text("Terms of Use")
                Text("|")
                Text("Privacy Policy")
            }
            .font(.caption)
            .foregroundColor(.gray.opacity(0.8))
            
            Text("By continuing, you agree to our terms")
                .font(.system(size: 10))
                .foregroundColor(.gray.opacity(0.5))
                .padding(.top, 8)
                .padding(.bottom, 10)
        }
    }
}
