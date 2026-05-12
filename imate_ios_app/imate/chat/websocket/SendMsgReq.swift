//
//  SendMsgReq.swift
//  imate
//
//  Created by 天之行 on 2026/5/9.
//

import Foundation

/// WebSocket 文本帧外层，对齐后端 / Android `ChatWebSocketReq`。
struct ChatWebSocketReq: Codable {
    let agent_id: String
    let request: SendMsgReq
}

/// 内层聊天请求体，对齐 Android `SendMsgReq`。
struct SendMsgReq: Codable {
    let messages: [SendMsgReqMessage]
    let model: String
    let stream: Bool
    let time_context: UserTimeContext?
    let target_imate_id: String?

    enum CodingKeys: String, CodingKey {
        case messages
        case model
        case stream
        case time_context
        case target_imate_id
    }
}

struct SendMsgReqMessage: Codable {
    let role: String
    /// 纯文本时序列化为 JSON 字符串，与 Android `JsonPrimitive(trimmed)` 一致。
    let content: String
}

struct UserTimeContext: Codable {
    let local_time: String
    let timezone: String
    let utc_offset_minutes: Int

    enum CodingKeys: String, CodingKey {
        case local_time
        case timezone
        case utc_offset_minutes
    }
}

extension SendMsgReq {
    /// 构造与 Android `ChatTextSendRequestFactory.buildTextSendMsgReq` 等价的请求体。
    static func userText(_ userText: String, agentId: String) -> SendMsgReq {
        let trimmed = userText.trimmingTrailingWhitespace()
        return SendMsgReq(
            messages: [
                SendMsgReqMessage(role: "user", content: trimmed),
            ],
            model: "chatbot",
            stream: false,
            time_context: UserTimeContext.now(),
            target_imate_id: agentId
        )
    }
}

extension ChatWebSocketReq {
    static func userMessage(agentId: String, text: String) -> ChatWebSocketReq {
        ChatWebSocketReq(agent_id: agentId, request: .userText(text, agentId: agentId))
    }
}

extension UserTimeContext {
    static func now() -> UserTimeContext {
        let tz = TimeZone.current
        let offsetMinutes = tz.secondsFromGMT() / 60
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.calendar = Calendar(identifier: .iso8601)
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"
        formatter.timeZone = tz
        let localTime = formatter.string(from: Date())
        return UserTimeContext(
            local_time: localTime,
            timezone: tz.identifier,
            utc_offset_minutes: offsetMinutes
        )
    }
}

private extension String {
    func trimmingTrailingWhitespace() -> String {
        var s = self
        while let last = s.last, last.isWhitespace {
            s.removeLast()
        }
        return s
    }
}
