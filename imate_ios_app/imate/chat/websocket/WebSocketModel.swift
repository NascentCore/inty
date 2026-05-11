//
//  WebSocketModel.swift
//  imate
//
//  Created by 天之行 on 2026/5/10.
//

import Foundation

struct WSResponse: Codable {
    let code: Int
    let message: String
    let data: [WSErrorItem]?
    let agentId: String?

    enum CodingKeys: String, CodingKey {
        case code
        case message
        case data
        case agentId = "agent_id"
    }
}

struct WSErrorItem: Codable {
    let type: String
    let loc: [String]
    let msg: String
    let input: InputData?
    let url: String
}

struct InputData: Codable {
    let content: String?
}
