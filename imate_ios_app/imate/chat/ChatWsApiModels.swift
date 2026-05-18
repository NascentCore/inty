import Foundation

/// Companion WebSocket ``messageType`` string (chat ``request`` body). Greeting uses ``user_signed_on``.
enum CompanionChatTurnMessageType {
    static let userMessage = "USER_MESSAGE"
}

struct SendMsgReqMessage: Codable {
    let role: String
    let content: String
}

/// HTTP-shaped completion body embedded in ``ChatWebSocketReq``; ``time_context`` is required on wire.
struct SendMsgReq: Codable {
    let messages: [SendMsgReqMessage]
    let model: String
    let stream: Bool
    let timeContext: UserTimeContext
    let targetImateId: String?
    let messageId: String?
    let messageType: String?

    enum CodingKeys: String, CodingKey {
        case messages
        case model
        case stream
        case timeContext = "time_context"
        case targetImateId = "target_imate_id"
        case messageId = "message_id"
        case messageType
    }
}

struct ChatWebSocketReq: Codable {
    let agentId: String
    let request: SendMsgReq

    enum CodingKeys: String, CodingKey {
        case agentId = "agent_id"
        case request
    }
}

struct ChatClientContextWsMessage: Codable {
    let type: String
    let timeContext: UserTimeContext

    enum CodingKeys: String, CodingKey {
        case type
        case timeContext = "time_context"
    }

    static func make(timeContext: UserTimeContext) -> ChatClientContextWsMessage {
        ChatClientContextWsMessage(type: "client_context", timeContext: timeContext)
    }
}

struct ChatUserSignedOnWsMessage: Codable {
    let type: String
    let agentId: String
    let messageId: String
    let timeContext: UserTimeContext

    enum CodingKeys: String, CodingKey {
        case type
        case agentId = "agent_id"
        case messageId = "message_id"
        case timeContext = "time_context"
    }

    static func make(agentId: String, messageId: String, timeContext: UserTimeContext) -> ChatUserSignedOnWsMessage {
        ChatUserSignedOnWsMessage(
            type: "user_signed_on",
            agentId: agentId,
            messageId: messageId,
            timeContext: timeContext
        )
    }
}

struct ChatUserSignedOutWsMessage: Codable {
    let type: String
    let agentId: String
    let messageId: String?
    let timeContext: UserTimeContext

    enum CodingKeys: String, CodingKey {
        case type
        case agentId = "agent_id"
        case messageId = "message_id"
        case timeContext = "time_context"
    }

    static func make(
        agentId: String,
        messageId: String?,
        timeContext: UserTimeContext
    ) -> ChatUserSignedOutWsMessage {
        ChatUserSignedOutWsMessage(
            type: "user_signed_out",
            agentId: agentId,
            messageId: messageId,
            timeContext: timeContext
        )
    }
}

struct ChatWsConnDroppedWsMessage: Codable {
    let type: String
    let agentId: String
    let droppedAtUtc: String
    let messageId: String?
    let timeContext: UserTimeContext
    let wsCloseCode: Int?
    let wsCloseReason: String?

    enum CodingKeys: String, CodingKey {
        case type
        case agentId = "agent_id"
        case droppedAtUtc = "dropped_at_utc"
        case messageId = "message_id"
        case timeContext = "time_context"
        case wsCloseCode = "ws_close_code"
        case wsCloseReason = "ws_close_reason"
    }

    static func make(
        agentId: String,
        droppedAtUtc: String,
        messageId: String?,
        timeContext: UserTimeContext,
        wsCloseCode: Int?,
        wsCloseReason: String?
    ) -> ChatWsConnDroppedWsMessage {
        ChatWsConnDroppedWsMessage(
            type: "ws_conn_dropped",
            agentId: agentId,
            droppedAtUtc: droppedAtUtc,
            messageId: messageId,
            timeContext: timeContext,
            wsCloseCode: wsCloseCode,
            wsCloseReason: wsCloseReason
        )
    }
}

struct ChatWsPingMessage: Codable {
    let type: String
    let timeContext: UserTimeContext

    enum CodingKeys: String, CodingKey {
        case type
        case timeContext = "time_context"
    }

    static func make(timeContext: UserTimeContext) -> ChatWsPingMessage {
        ChatWsPingMessage(type: "ping", timeContext: timeContext)
    }
}

struct ChatWsControlFrame: Codable {
    let type: String?
}

extension ChatWsControlFrame? {
    func shouldDeferChatResponseParsing() -> Bool {
        guard let type else { return false }
        switch type {
        case "pong", "client_context_ack", "user_signed_on_ack", "user_signed_out_ack", "ws_conn_dropped_ack":
            return true
        default:
            return false
        }
    }
}

struct SendMsgResponse: Codable {
    let code: Int?
    let message: String?
    let agentId: String?

    enum CodingKeys: String, CodingKey {
        case code
        case message
        case agentId = "agent_id"
    }
}
