import Foundation

private let chatWebSocketPath = "api/v1/chat/ws"
/// Server closes idle sockets without inbound text within ``chat_ws_idle_timeout_seconds`` (min 10s).
private let pingIntervalNs: UInt64 = 9_000_000_000
private let waitSessionStepNs: UInt64 = 50_000_000
private let waitSessionTimeoutNs: UInt64 = 30_000_000_000

/// Companion ``/api/v1/chat/ws`` client; every uplink JSON includes top-level or nested ``time_context``.
@MainActor
final class ChatWebSocketRemoteDataSource: ObservableObject {
    @Published private(set) var isSessionActive = false

    private var task: URLSessionWebSocketTask?
    private var pingTask: Task<Void, Never>?
    private var receiveTask: Task<Void, Never>?
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()
    private var userSignedOnAgentIdForConnection: String?
    private var implicitSignOnSentAgentIds: Set<String> = []

    var onChatResponse: ((SendMsgResponse) -> Void)?

    func connectWebsocket(baseURL: URL, bearerToken: String, wsConnId: String = UUID().uuidString) {
        disconnect()
        guard let url = Self.buildChatWebSocketURL(httpBase: baseURL, wsConnId: wsConnId) else {
            return
        }
        var request = URLRequest(url: url)
        request.setValue("Bearer \(bearerToken)", forHTTPHeaderField: "Authorization")
        let task = URLSession.shared.webSocketTask(with: request)
        self.task = task
        userSignedOnAgentIdForConnection = nil
        implicitSignOnSentAgentIds = []
        isSessionActive = true
        task.resume()
        startPingLoop()
        startReceiveLoop()
    }

    func disconnect() {
        pingTask?.cancel()
        pingTask = nil
        receiveTask?.cancel()
        receiveTask = nil
        task?.cancel(with: .normalClosure, reason: nil)
        task = nil
        userSignedOnAgentIdForConnection = nil
        implicitSignOnSentAgentIds = []
        isSessionActive = false
    }

    func sendClientContext() async throws {
        try await sendJSON(ChatClientContextWsMessage.make(timeContext: UserTimeContextBuilder.buildNow()))
    }

    func sendImplicitUserSignedOnFireAndForget(agentId: String) async throws {
        let aid = agentId.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !aid.isEmpty else { return }
        try await waitUntilSessionReadyOrThrow()
        if implicitSignOnSentAgentIds.contains(aid) {
            return
        }
        let messageId = UUID().uuidString
        try await sendJSON(
            ChatUserSignedOnWsMessage.make(
                agentId: aid,
                messageId: messageId,
                timeContext: UserTimeContextBuilder.buildNow()
            )
        )
        userSignedOnAgentIdForConnection = aid
        implicitSignOnSentAgentIds.insert(aid)
    }

    func sendUserSignedOn(agentId: String, messageId: String) async throws {
        try await waitUntilSessionReadyOrThrow()
        try await sendJSON(
            ChatUserSignedOnWsMessage.make(
                agentId: agentId,
                messageId: messageId,
                timeContext: UserTimeContextBuilder.buildNow()
            )
        )
        userSignedOnAgentIdForConnection = agentId
    }

    func sendUserSignedOut(agentId: String, messageId: String?) async throws {
        try await waitUntilSessionReadyOrThrow()
        try await sendJSON(
            ChatUserSignedOutWsMessage.make(
                agentId: agentId,
                messageId: messageId,
                timeContext: UserTimeContextBuilder.buildNow()
            )
        )
    }

    func sendWsConnDropped(
        agentId: String,
        droppedAtUtc: String,
        messageId: String?,
        wsCloseCode: Int?,
        wsCloseReason: String?
    ) async throws {
        try await waitUntilSessionReadyOrThrow()
        try await sendJSON(
            ChatWsConnDroppedWsMessage.make(
                agentId: agentId,
                droppedAtUtc: droppedAtUtc,
                messageId: messageId,
                timeContext: UserTimeContextBuilder.buildNow(),
                wsCloseCode: wsCloseCode,
                wsCloseReason: wsCloseReason
            )
        )
    }

    func sendMessageFireAndForget(agentId: String, request: SendMsgReq) async throws {
        try await waitUntilSessionReadyOrThrow()
        if userSignedOnAgentIdForConnection != agentId {
            try await sendJSON(
                ChatUserSignedOnWsMessage.make(
                    agentId: agentId,
                    messageId: UUID().uuidString,
                    timeContext: UserTimeContextBuilder.buildNow()
                )
            )
            userSignedOnAgentIdForConnection = agentId
        }
        let payload = ChatWebSocketReq(agentId: agentId, request: request)
        try await sendJSON(payload)
    }

    func sendTextMessageFireAndForget(agentId: String, userText: String) async throws {
        let request = ChatTextSendRequestFactory.buildTextSendMsgReq(agentId: agentId, userText: userText)
        try await sendMessageFireAndForget(agentId: agentId, request: request)
    }

    static func buildChatWebSocketURL(httpBase: URL, wsConnId: String) -> URL? {
        var components = URLComponents(url: httpBase, resolvingAgainstBaseURL: false)
        let scheme: String
        switch components?.scheme?.lowercased() {
        case "https":
            scheme = "wss"
        case "http":
            scheme = "ws"
        case "wss", "ws":
            scheme = components?.scheme ?? "ws"
        default:
            scheme = "ws"
        }
        components?.scheme = scheme
        var path = components?.path ?? ""
        if path.hasSuffix("/") {
            path.removeLast()
        }
        components?.path = "\(path)/\(chatWebSocketPath)"
        components?.queryItems = [URLQueryItem(name: "ws_conn_id", value: wsConnId)]
        return components?.url
    }

    static func droppedAtUtcNow() -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        formatter.timeZone = TimeZone(secondsFromGMT: 0)
        return formatter.string(from: Date())
    }

    private func startPingLoop() {
        pingTask = Task { [weak self] in
            while !Task.isCancelled {
                guard let self else { return }
                if let task = self.task {
                    let ping = ChatWsPingMessage.make(timeContext: UserTimeContextBuilder.buildNow())
                    if let text = try? self.encodeJSONString(ping) {
                        try? await task.send(.string(text))
                    }
                }
                try? await Task.sleep(nanoseconds: pingIntervalNs)
            }
        }
    }

    private func startReceiveLoop() {
        receiveTask = Task { [weak self] in
            guard let self else { return }
            await self.receiveLoop()
        }
    }

    private func receiveLoop() async {
        guard let task else { return }
        while !Task.isCancelled {
            do {
                let message = try await task.receive()
                guard case .string(let text) = message else { continue }
                guard let data = text.data(using: .utf8) else { continue }
                let control = try? decoder.decode(ChatWsControlFrame.self, from: data)
                if control.shouldDeferChatResponseParsing() {
                    continue
                }
                if let response = try? decoder.decode(SendMsgResponse.self, from: data) {
                    onChatResponse?(response)
                }
            } catch {
                if !Task.isCancelled {
                    disconnect()
                }
                return
            }
        }
    }

    private func waitUntilSessionReadyOrThrow() async throws {
        let deadline = DispatchTime.now().uptimeNanoseconds + waitSessionTimeoutNs
        while task == nil {
            if DispatchTime.now().uptimeNanoseconds >= deadline {
                throw ChatWebSocketError.notConnected
            }
            try await Task.sleep(nanoseconds: waitSessionStepNs)
        }
    }

    private func sendJSON<T: Encodable>(_ value: T) async throws {
        guard let task else {
            throw ChatWebSocketError.notConnected
        }
        let text = try encodeJSONString(value)
        try await task.send(.string(text))
    }

    private func encodeJSONString<T: Encodable>(_ value: T) throws -> String {
        let data = try encoder.encode(value)
        guard let text = String(data: data, encoding: .utf8) else {
            throw ChatWebSocketError.encodeFailed
        }
        return text
    }
}

enum ChatWebSocketError: Error {
    case notConnected
    case encodeFailed
}
