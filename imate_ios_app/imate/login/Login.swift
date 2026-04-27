//
//  Login.swift
//  imate
//
//  Created by 天之行 on 2026/4/19.
//

import SwiftUI
import Foundation

struct LoginView: View {
    
    @EnvironmentObject var router: Router
    
    var body: some View {
        ZStack {
            LoginWidgets.HeaderBg()
            
            VStack(spacing: 0) {
                Spacer(minLength: 50)
                LoginWidgets.IconAbout()
                
                Spacer()
                LoginWidgets.DescView()
                
                Spacer().frame(height: 30)
                LoginWidgets.ButtonView(
                    onAppleAction: goAppleLogin, onEmailAction: goEmailLogin
                )
                
                Spacer(minLength: 40)
                LoginWidgets.TermsView()
            }
        }
    }
    
    private func goAppleLogin() {
        ToastManager.shared.show("正在接入中...", type: .info);
    }
    
    private func goEmailLogin() {
        router.push(.loginEmail)
    }
    
    
//    func fetchProfile() async {
//        do {
//            let cb: LoginResponse = try await NetworkService.shared.request(UserAPI.login(email: "1@qq.com", password: "341"));
//            print("on release data val si ------->\(cb.token)");
//        } catch {
//            print("on error si val----->\(error)")
//            ToastManager.shared.show("on login error \(error)", duration: 5, type: .error);
//        }
//    }
}
