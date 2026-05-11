//
//  SendMsgResponse.swift
//  imate
//
//  Created by 天之行 on 2026/5/9.
//

import Foundation

struct SendMsgResponse: Codable, Identifiable {
//    var id = UUID()
//    let message: String
    var id = UUID()
    let msg: String?
}
