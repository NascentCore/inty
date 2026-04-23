//
//  Login.swift
//  imate
//
//  Created by 天之行 on 2026/4/19.
//

import SwiftUI

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
        router.push(.LoginInitChat)
    }
    
    private func goEmailLogin() {
        router.push(.loginEmail)
    }
}
