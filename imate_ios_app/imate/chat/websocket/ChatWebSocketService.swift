//
//  ChatWebSocketService.swift
//  imate
//
//  Created by 天之行 on 2026/5/9.
//

import Foundation

final class ChatWebSocketService {

    private var webSocketTask: URLSessionWebSocketTask?
    private var pingTimer: Timer?

    var onReceiveMessage: ((ChatCompletionData) -> Void)?
    var onConnectionChanged: ((Bool) -> Void)?

    // MARK: - Connect
    func connect() {
        guard let url = URL(string: "wss://dev.imate.inty.cc/api/v1/chat/ws") else {
            return
        }
        
        var request = URLRequest(url: url)
        request.addValue("Bearer \(UserManager.shared.token ?? "")", forHTTPHeaderField: "Authorization")
        
        webSocketTask = URLSession.shared.webSocketTask(with: request)
        webSocketTask?.resume()
        startPing()
        receiveMessage()
        DispatchQueue.main.async {
            self.onConnectionChanged?(true)
        }
    }

    // MARK: - Disconnect
    func disconnect() {
        pingTimer?.invalidate()
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        DispatchQueue.main.async {
            self.onConnectionChanged?(false)
        }
    }

    // MARK: - Send
    func send(message: ChatWebSocketReq) {
        guard let task = webSocketTask else {
            return
        }

        do {
            let data = try JSONEncoder().encode(message)
            if let jsonString = String(data: data, encoding: .utf8) {
                task.send(.string(jsonString)) { error in
                    if let error = error {
                        print("Send Error:", error)
                    }
                }
            }
        } catch {
            print(error)
        }
    }

    // MARK: - Receive
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .failure(let error):
                print("Receive Error:", error)
                self.reconnect()
            case .success(let message):
                switch message {
                case .string(let text):
                    self.handleTextMessage(text)
                default:
                    break
                }
                self.receiveMessage()
            }
        }
    }

    // MARK: - Handle Message
    private func handleTextMessage(_ text: String) {
        guard let data = text.data(using: .utf8) else {
            return
        }
//        print("on response data val si ------->\(text)")
        
        
        do {
            let response = try JSONDecoder().decode(WSResponse.self, from: data)
//            print("on response si --------->\(response.code)----->\(response.data.choices[0].message.content)")
            
            if response.code != 200 {
                DispatchQueue.main.async {
                    ToastManager.shared.show(response.message)
                }
            }
            
            DispatchQueue.main.async {
                self.onReceiveMessage?(response.data)
            }

        } catch {
            print("Decode Error:", error)
        }
    }

    // MARK: - Ping
    private func startPing() {
        pingTimer?.invalidate()
        pingTimer = Timer.scheduledTimer(
            withTimeInterval: 9,
            repeats: true
        ) { [weak self] _ in
            self?.webSocketTask?.sendPing { error in
                if let error = error {
                    print("Ping Error:", error)
                    self?.reconnect()
                }
            }
        }
    }

    // MARK: - Reconnect
    private func reconnect() {
        disconnect()
        DispatchQueue.main.asyncAfter(deadline: .now() + 5) {
            self.connect()
        }
    }
}
