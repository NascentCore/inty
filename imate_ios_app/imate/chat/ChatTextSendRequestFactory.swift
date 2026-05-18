import Foundation

enum ChatTextSendRequestFactory {
    static func buildTextSendMsgReq(agentId: String, userText: String) -> SendMsgReq {
        var trimmed = userText
        while let last = trimmed.unicodeScalars.last,
              CharacterSet.whitespacesAndNewlines.contains(last)
        {
            trimmed.removeLast()
        }
        return SendMsgReq(
            messages: [SendMsgReqMessage(role: "user", content: trimmed)],
            model: "chatbot",
            stream: false,
            timeContext: UserTimeContextBuilder.buildNow(),
            targetImateId: agentId,
            messageId: UUID().uuidString,
            messageType: CompanionChatTurnMessageType.userMessage
        )
    }
}
