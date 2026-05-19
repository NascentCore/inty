//
//  WebSocketModel.swift
//  imate
//
//  Created by 天之行 on 2026/5/10.
//

import Foundation

//struct WSResponse: Codable {
//    let code: Int
//    let message: String
//    let data: [WSErrorItem]?
//    let agentId: String?
//
//    enum CodingKeys: String, CodingKey {
//        case code
//        case message
//        case data
//        case agentId = "agent_id"
//    }
//}
//
//struct WSErrorItem: Codable {
//    let type: String
//    let loc: [String]
//    let msg: String
//    let input: InputData?
//    let url: String
//}
//
//struct InputData: Codable {
//    let content: String?
//}

import Foundation

// MARK: - Root Response
struct WSResponse: Codable {
    let code: Int
    let message: String
    let data: ChatCompletionData
    let statusLine: String?
    let agentId: String?

    enum CodingKeys: String, CodingKey {
        case code
        case message
        case data
        case statusLine = "status_line"
        case agentId = "agent_id"
    }
}

// MARK: - Data
struct ChatCompletionData: Codable {
    let id: String
    let object: String
    let created: Int
    let model: String
    let userMessageId: Int
    let businessActions: [BusinessAction]
    let choices: [Choice]
    let usage: Usage
    let sourceImateId: String
    let localId: String

    enum CodingKeys: String, CodingKey {
        case id
        case object
        case created
        case model
        case userMessageId = "user_message_id"
        case businessActions = "business_actions"
        case choices
        case usage
        case sourceImateId = "source_imate_id"
        case localId = "local_id"
    }
}

// MARK: - Business Action
struct BusinessAction: Codable {
    let actionType: String
    let message: String

    enum CodingKeys: String, CodingKey {
        case actionType = "action_type"
        case message
    }
}

// MARK: - Choice
struct Choice: Codable {
    let index: Int
    let message: AssistantMessage
    let finishReason: String

    enum CodingKeys: String, CodingKey {
        case index
        case message
        case finishReason = "finish_reason"
    }
}

// MARK: - Assistant Message
struct AssistantMessage: Codable {
    let role: String
    let content: String
    let id: Int
    let metaData: MessageMetaData?
    let timestamp: String
    let audioURL: String?

    enum CodingKeys: String, CodingKey {
        case role
        case content
        case id
        case metaData = "meta_data"
        case timestamp
        case audioURL = "audio_url"
    }
}

// MARK: - Message Meta Data
struct MessageMetaData: Codable {
    let source: String?
    let agentId: String?
    let traceId: String?
    let isOpening: Bool?
    let contextMode: String?
    let userMsgUUID: String?
    let replyModality: String?
    let langsmithRunId: String?
    let langsmithTraceId: String?
    let significancePerception: SignificancePerception?
    let toolBackgroundStarted: Bool?

    enum CodingKeys: String, CodingKey {
        case source
        case agentId
        case traceId = "trace_id"
        case isOpening
        case contextMode = "context_mode"
        case userMsgUUID = "user_msg_uuid"
        case replyModality = "reply_modality"
        case langsmithRunId = "langsmith_run_id"
        case langsmithTraceId = "langsmith_trace_id"
        case significancePerception = "significance_perception"
        case toolBackgroundStarted = "tool_background_started"
    }
}

// MARK: - Significance Perception
struct SignificancePerception: Codable {
    let importanceRound: Int?
    let importanceUserMessage: Int?
    let importanceAssistantMessage: Int?

    enum CodingKeys: String, CodingKey {
        case importanceRound = "importance_round"
        case importanceUserMessage = "importance_user_message"
        case importanceAssistantMessage = "importance_assistant_message"
    }
}

// MARK: - Usage
struct Usage: Codable {
    let promptTokens: Int
    let completionTokens: Int
    let totalTokens: Int

    enum CodingKeys: String, CodingKey {
        case promptTokens = "prompt_tokens"
        case completionTokens = "completion_tokens"
        case totalTokens = "total_tokens"
    }
}
