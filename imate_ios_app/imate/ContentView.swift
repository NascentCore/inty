//
//  ContentView.swift
//  imate
//
//  Created by 天之行 on 2026/4/18.
//

import SwiftUI

struct IMateLoginView: View {
    var body: some View {
        ZStack {
            // --- 背景渐变 ---
            LinearGradient(
                gradient: Gradient(colors: [Color(white: 0.15), Color.black]),
                startPoint: .top,
                endPoint: .bottom
            )
            .ignoresSafeArea()

            VStack(spacing: 0) {
                Spacer(minLength: 50)

                // --- 顶部 Logo 区域 ---
                VStack(spacing: 20) {
                    // 这里模拟图标，实际开发中请替换为您的 Image("logo_name")
                    ZStack {
                        Circle()
                            .stroke(Color.blue.opacity(0.3), lineWidth: 1)
                            .frame(width: 140, height: 140)
                        
                        // 内部发光球体
                        Circle()
                            .fill(
                                RadialGradient(
                                    gradient: Gradient(colors: [Color.blue.opacity(0.8), Color.blue.opacity(0.2)]),
                                    center: .center,
                                    startRadius: 5,
                                    endRadius: 40
                                )
                            )
                            .frame(width: 80, height: 80)
                            .shadow(color: .blue.opacity(0.5), radius: 20)
                        
                        // 模拟装饰线条
                        Image(systemName: "scope")
                            .resizable()
                            .foregroundColor(.white.opacity(0.6))
                            .frame(width: 120, height: 120)
                    }

                    Text("iMate")
                        .font(.system(size: 42, weight: .bold))
                        .foregroundColor(.white)

                    Text("Your AI, your way")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                }

                Spacer()

                // --- 中间介绍卡片 ---
                VStack {
                    Text("Meet your personalized AI companion —\nbuilt around ")
                        .foregroundColor(.gray) +
                    Text("you")
                        .foregroundColor(.blue)
                        .fontWeight(.semibold) +
                    Text(", growing with every\nconversation.")
                        .foregroundColor(.gray)
                }
                .multilineTextAlignment(.center)
                .lineSpacing(4)
                .padding(.horizontal, 40)
                .padding(.vertical, 30)
                .background(
                    RoundedRectangle(cornerRadius: 30)
                        .fill(Color(white: 0.12))
                )
                .padding(.horizontal, 30)

                Spacer().frame(height: 30)

                // --- 按钮区域 ---
                VStack(spacing: 20) {
                    // Google 登录按钮
                    Button(action: {
                        print("Continue with Google")
                    }) {
                        HStack {
                            Image(systemName: "g.circle.fill") // 模拟 Google 图标
                                .font(.title3)
                            Text("Continue with Google")
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
                        print("Continue with Email")
                    }
                    .font(.subheadline)
                    .foregroundColor(.gray)
                }
                .padding(.horizontal, 30)

                Spacer(minLength: 40)

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
}

// 预览
struct IMateLoginView_Previews: PreviewProvider {
    static var previews: some View {
        IMateLoginView()
            .preferredColorScheme(.dark)
    }
}
