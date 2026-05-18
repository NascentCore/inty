import Foundation
import Combine

@MainActor
final class VoiceCallWebSocketClient: ObservableObject {
    @Published var state: VoiceCallConnectionState = .disconnected
    @Published var remainingDuration: Int?
    @Published var lastError: String?

    private var task: URLSessionWebSocketTask?
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    func connect(baseURL: URL, token: String, agentId: String, onAudio: @escaping (Data) -> Void) {
        close()
        state = .connecting
        lastError = nil

        var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false)
        let scheme = components?.scheme == "https" ? "wss" : "ws"
        components?.scheme = scheme
        components?.path = "/api/v1/live-chat/\(agentId)"
        components?.queryItems = [URLQueryItem(name: "agent_starts_conversation", value: "true")]
        guard let url = components?.url else {
            state = .error
            lastError = "Invalid voice-call URL"
            return
        }

        var request = URLRequest(url: url)
        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let task = URLSession.shared.webSocketTask(with: request)
        self.task = task
        task.resume()
        state = .connected
        receiveLoop(onAudio: onAudio)
    }

    func sendAudio(_ data: Data) {
        guard let task else { return }
        let packet = VoiceCallPacket(type: .audio, data: data.base64EncodedString())
        guard let encoded = try? encoder.encode(packet),
              let text = String(data: encoded, encoding: .utf8)
        else { return }
        task.send(.string(text)) { _ in }
    }

    func close() {
        task?.send(.string(#"{"type":"end"}"#)) { _ in }
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
        state = .disconnected
    }

    private func receiveLoop(onAudio: @escaping (Data) -> Void) {
        task?.receive { [weak self] result in
            Task { @MainActor in
                guard let self else { return }
                switch result {
                case .failure(let error):
                    self.lastError = error.localizedDescription
                    self.state = .error
                    return
                case .success(let message):
                    if case .string(let text) = message,
                       let data = text.data(using: .utf8),
                       let packet = try? self.decoder.decode(VoiceCallPacket.self, from: data) {
                        self.handle(packet, onAudio: onAudio)
                    }
                    self.receiveLoop(onAudio: onAudio)
                }
            }
        }
    }

    private func handle(_ packet: VoiceCallPacket, onAudio: @escaping (Data) -> Void) {
        switch packet.type {
        case .audioResponse:
            if let raw = packet.data, let data = Data(base64Encoded: raw) {
                onAudio(data)
            }
        case .sessionInfo:
            remainingDuration = packet.remainingDuration
        case .error:
            lastError = packet.message ?? packet.errorCode ?? "Voice call failed"
            state = .error
        case .end:
            close()
        default:
            break
        }
    }
}
