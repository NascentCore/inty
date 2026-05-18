import Foundation

enum VoiceCallPacketType: String, Codable {
    case audio = "audio"
    case audioResponse = "audio_response"
    case status
    case error
    case sessionInfo = "session_info"
    case transcript
    case userTranscript = "user_transcript"
    case end
}

struct VoiceCallPacket: Codable {
    var type: VoiceCallPacketType
    var data: String?
    var status: String?
    var message: String?
    var errorCode: String?
    var remainingDuration: Int?

    enum CodingKeys: String, CodingKey {
        case type
        case data
        case status
        case message
        case errorCode = "error_code"
        case remainingDuration = "remaining_duration"
    }
}

enum VoiceCallConnectionState: String {
    case disconnected
    case connecting
    case connected
    case error
}
