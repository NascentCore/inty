import AVFoundation
import SwiftUI

struct VoiceCallView: View {
    @StateObject private var client = VoiceCallWebSocketClient()
    private let audio = VoiceCallAudioEngine()

    let baseURL: URL
    let token: String
    let agentId: String
    let agentName: String

    var body: some View {
        VStack(spacing: 24) {
            Circle()
                .fill(.purple.opacity(0.24))
                .frame(width: 112, height: 112)
                .overlay(Text(String(agentName.prefix(1))).font(.largeTitle.bold()))
            Text(agentName).font(.title2.bold())
            Text(statusText).foregroundStyle(.secondary)
            if let remaining = client.remainingDuration {
                Text("\(remaining) seconds remaining").font(.footnote).foregroundStyle(.secondary)
            }
            HStack(spacing: 24) {
                Button("Start") {
                    start()
                }
                .buttonStyle(.borderedProminent)
                Button("End") {
                    stop()
                }
                .buttonStyle(.bordered)
            }
        }
        .padding()
        .onDisappear { stop() }
    }

    private var statusText: String {
        if let err = client.lastError { return err }
        switch client.state {
        case .disconnected: return "Voice call ended"
        case .connecting: return "Connecting voice call…"
        case .connected: return "Connected — speak naturally"
        case .error: return "Voice call failed"
        }
    }

    private func start() {
        Task {
            let granted = await requestMicrophone()
            guard granted else { return }
            try? audio.start { data in
                Task { @MainActor in client.sendAudio(data) }
            }
            client.connect(baseURL: baseURL, token: token, agentId: agentId) { data in
                audio.playPcm24k(data)
            }
        }
    }

    private func stop() {
        client.close()
        audio.stop()
    }

    private func requestMicrophone() async -> Bool {
        await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }
}

#Preview {
    VoiceCallView(
        baseURL: URL(string: "https://example.com")!,
        token: "dev-token",
        agentId: "agent-id",
        agentName: "iMate"
    )
}
