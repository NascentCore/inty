//
//  ChatRepository.swift
//  imate
//
//  Created by 天之行 on 2026/5/9.
//

import Foundation

final class ChatRepository {

    let service = ChatWebSocketService()

    func connect() {
        service.connect()
    }

    func disconnect() {
        service.disconnect()
    }

    func send(message: ChatWebSocketReq) {
        service.send(message: message)
    }
}
