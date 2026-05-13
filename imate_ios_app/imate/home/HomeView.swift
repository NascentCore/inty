//
//  ContentView.swift
//  imate
//
//  Created by 天之行 on 2026/4/18.
//

import SwiftUI

struct HomeView: View {
    @State private var baseURL = "https://localhost:8000"
    @State private var token = ""
    @State private var agentId = ""
    @State private var showVoiceCall = false

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "phone.circle.fill")
                .font(.system(size: 56))
                .foregroundStyle(.tint)
            Text("iMate Voice Call")
                .font(.title2.bold())
            TextField("Backend base URL", text: $baseURL)
                .textInputAutocapitalization(.never)
                .textFieldStyle(.roundedBorder)
            SecureField("Bearer token", text: $token)
                .textInputAutocapitalization(.never)
                .textFieldStyle(.roundedBorder)
            TextField("Agent ID", text: $agentId)
                .textInputAutocapitalization(.never)
                .textFieldStyle(.roundedBorder)
            Button("Start realtime voice call") {
                showVoiceCall = true
            }
            .buttonStyle(.borderedProminent)
            .disabled(URL(string: baseURL) == nil || token.isEmpty || agentId.isEmpty)
        }
        .padding()
        .sheet(isPresented: $showVoiceCall) {
            VoiceCallView(
                baseURL: URL(string: baseURL)!,
                token: token,
                agentId: agentId,
                agentName: "iMate"
            )
        }
    }
}

#Preview {
    HomeView()
}
