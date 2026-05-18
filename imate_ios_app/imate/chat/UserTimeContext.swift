import Foundation

/// Wall-clock context for ``/api/v1/chat/ws`` uplinks (control frames and chat ``request``).
struct UserTimeContext: Codable, Equatable, Sendable {
    let localTime: String
    let timezone: String
    let utcOffsetMinutes: Int

    enum CodingKeys: String, CodingKey {
        case localTime = "local_time"
        case timezone
        case utcOffsetMinutes = "utc_offset_minutes"
    }
}

enum UserTimeContextBuilder {
    /// Device local time + IANA timezone + UTC offset (matches Android ``buildUserTimeContext`` / REPL).
    static func buildNow() -> UserTimeContext {
        let now = Date()
        let tz = TimeZone.current
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        formatter.timeZone = tz
        let localTime = formatter.string(from: now)
        assert(!localTime.isEmpty)
        return UserTimeContext(
            localTime: localTime,
            timezone: tz.identifier,
            utcOffsetMinutes: tz.secondsFromGMT(for: now) / 60
        )
    }
}
