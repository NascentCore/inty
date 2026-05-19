//
//  RootView.swift
//  imate
//
//  Created by 天之行 on 2026/5/12.
//

import SwiftUI

struct RootView: View {

    @StateObject private var user = UserManager.shared
    
    var body: some View {
        Group {
            if user.isLogin {
                HomeView()
            } else {
                Entrance()
            }
        }
    }
}
