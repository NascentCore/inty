//
//  LoginAuth.swift
//  imate
//
//  Created by 天之行 on 2026/4/21.
//

import SwiftUI

// 模拟 Dot 数据结构
struct Dot: Hashable {
    let x: CGFloat
    let y: CGFloat
    let size: CGFloat
    let color: Color
    let opacity: Double
}

struct LoginAuth: View {
    // 参数回调
//    var onLoginSuccess: () -> Void
    
    // 状态管理
    @State private var progress: CGFloat = 0.0
    @State private var isLoginFinished: Bool = false // 模拟 ViewModel 的 isLogin
    
    // 预定义粒子数据 (从原代码坐标等比移植)
    private let dots: [Dot] = [
        Dot(x: 315.40, y: 362.22, size: 7.295, color: Color(hex: 0x2C7BB6), opacity: 0.86),
            Dot(x: 275.23, y: 376.17, size: 4.475, color: Color(hex: 0x5BA3D4), opacity: 0.90),
            Dot(x: 309.46, y: 400.99, size: 3.63,  color: Color(hex: 0xC3F0FD), opacity: 0.02),
            Dot(x: 332.66, y: 434.36, size: 2.265, color: Color(hex: 0x7EC8E3), opacity: 0.06),
            Dot(x: 281.74, y: 450.74, size: 2.22,  color: Color(hex: 0x5BA3D4), opacity: 0.05),
            Dot(x: 266.24, y: 462.28, size: 4.61,  color: Color(hex: 0xC3F0FD), opacity: 0.24),
            Dot(x: 266.58, y: 503.72, size: 1.663, color: Color(hex: 0x7EC8E3), opacity: 0.05),
            Dot(x: 216.42, y: 436.29, size: 8.586, color: Color(hex: 0x2C7BB6), opacity: 0.84),
            Dot(x: 219.17, y: 512.98, size: 1.599, color: Color(hex: 0x5BA3D4), opacity: 0.03),
            Dot(x: 193.67, y: 448.89, size: 5.936, color: Color(hex: 0xC3F0FD), opacity: 0.44),
            Dot(x: 186.67, y: 416.81, size: 3.032, color: Color(hex: 0x7EC8E3), opacity: 0.46),
            Dot(x: 160.50, y: 432.61, size: 2.262, color: Color(hex: 0x5BA3D4), opacity: 0.06),
            Dot(x: 153.61, y: 420.31, size: 3.494, color: Color(hex: 0xC3F0FD), opacity: 0.60),
            Dot(x: 112.35, y: 424.50, size: 2.184, color: Color(hex: 0x2C7BB6), opacity: 0.21),
            Dot(x: 88.62,  y: 416.82, size: 4.675, color: Color(hex: 0x5BA3D4), opacity: 0.60),
            Dot(x: 141.24, y: 378.28, size: 8.445, color: Color(hex: 0xC3F0FD), opacity: 0.85),
            Dot(x: 101.31, y: 376.96, size: 5.847, color: Color(hex: 0x7EC8E3), opacity: 0.60),
            Dot(x: 93.50,  y: 347.75, size: 3.228, color: Color(hex: 0x5BA3D4), opacity: 0.13),
            Dot(x: 148.56, y: 347.06, size: 8.857, color: Color(hex: 0xC3F0FD), opacity: 0.69),
            Dot(x: 96.56,  y: 265.56, size: 4.914, color: Color(hex: 0x5BA3D4), opacity: 0.44),
            Dot(x: 132.38, y: 277.77, size: 2.574, color: Color(hex: 0xC3F0FD), opacity: 0.13),
            Dot(x: 177.83, y: 312.93, size: 4.195, color: Color(hex: 0x2C7BB6), opacity: 0.49),
            Dot(x: 176.42, y: 256.80, size: 7.49,  color: Color(hex: 0x5BA3D4), opacity: 0.90),
            Dot(x: 193.85, y: 293.92, size: 5.107, color: Color(hex: 0xC3F0FD), opacity: 0.77),
            Dot(x: 213.55, y: 305.28, size: 3.858, color: Color(hex: 0x2C7BB6), opacity: 0.13),
            Dot(x: 265.16, y: 267.22, size: 3.338, color: Color(hex: 0xC3F0FD), opacity: 0.15),
            Dot(x: 234.26, y: 322.25, size: 5.126, color: Color(hex: 0x7EC8E3), opacity: 0.32),
            Dot(x: 259.35, y: 317.66, size: 2.139, color: Color(hex: 0x2C7BB6), opacity: 0.51),
            Dot(x: 281.86, y: 331.66, size: 8.999, color: Color(hex: 0xC3F0FD), opacity: 0.90),
            Dot(x: 295.92, y: 348.30, size: 2.646, color: Color(hex: 0x7EC8E3), opacity: 0.03)
    ]

    var body: some View {
        ZStack {
            // --- 背景层
            LoginWidgets.HeaderBg()

            // --- 绘图层：Canvas 绘制圆环与粒子 ---
            Canvas { context, size in
                let center = CGPoint(x: size.width / 2, y: size.height / 2)
                
                // 绘制装饰圆环
                let ringRadii: [CGFloat] = [317.28, 278.92, 130.56, 80.0]
                let opacities: [Double] = [0.21, 0.44, 0.73, 0.80]
                
                for (index, radius) in ringRadii.enumerated() {
                    context.stroke(
                        Path(ellipseIn: CGRect(
                            x: center.x - radius/2, y: center.y - radius/2,
                            width: radius, height: radius)),
                        with: .color(Color(hex: 0x2C7BB6, alpha: opacities[index])),
                        lineWidth: 1.5
                    )
                }

                // 绘制随机粒子
                for dot in dots {
                    let rect = CGRect(x: dot.x - dot.size/2, y: dot.y - dot.size/2, width: dot.size, height: dot.size)
                    context.fill(
                        Path(ellipseIn: rect),
                        with: .color(dot.color.opacity(dot.opacity))
                    )
                }
            }

            // --- 内容层：Logo 与 文字 ---
            VStack(spacing: 0) {
                Image("logo") // 请确保 Assets 中有此图片
                    .resizable()
                    .frame(width: 96, height: 96)
                
                Spacer().frame(height: 24)
                
                Text("iMate")
                    .font(.system(size: 28, weight: .bold))
                    .tracking(7)
                    .foregroundColor(.white)
                
                Spacer().frame(height: 8)
                
                Text("Your personalized AI companion")
                    .font(.system(size: 13))
                    .tracking(1.56)
                    .foregroundColor(Color(hex: 0xC3F0FD, alpha: 0.7))
            }

            // --- 底部层：进度条 ---
            VStack {
                Spacer()
                ZStack(alignment: .leading) {
                    // 进度条背景
                    Capsule()
                        .fill(Color(hex: 0x3C3445, alpha: 0.8))
                        .frame(width: 329, height: 2)
                    
                    // 进度条前景
                    Capsule()
                        .fill(Color(hex: 0xFF5BA3D4))
                        .frame(width: 329 * progress, height: 2)
                }
                .padding(.bottom, 64)
            }
        }
        .onAppear {
            startLoadingSequence()
        }
        .navigationBarBackButtonHidden(true)
    }
    
    // --- 动画逻辑：模拟 Kotlin 的协程控制 ---
    private func startLoadingSequence() {
        // 第一阶段：2秒内加载到 80%
        withAnimation(.linear(duration: 2.0)) {
            progress = 0.8
        }
        
        // 模拟登录状态检查（原代码中的 loginTrue.await）
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
            isLoginFinished = true
            
            // 第二阶段：完成后冲刺到 100% 并回调
            withAnimation(.linear(duration: 0.1)) {
                progress = 1.0
            }
            
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
//                onLoginSuccess()
                print("on  animation end ------>")
            }
        }
    }
}
