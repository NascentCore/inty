# Phone calls

- Implemented default-on phone-call surfaces across backend, iMate Android, and iMate iOS.

## Actions

- Added Twilio outbound/inbound PSTN bridge APIs and Twilio Media Streams WebSocket.
- Added privacy-preserving caller bindings with HMAC phone lookup and Alembic migration.
- Added companion tool plus deterministic `Call me at ...` chat trigger.
- Added iMate Android realtime voice-call overlay using the existing Live Chat protocol.
- Added iMate iOS minimal realtime voice-call client and SwiftUI surface.
- Documented phone-call API, security boundaries, and user-facing voice-call behavior.

## Follow-ups

- Real PSTN end-to-end smoke requires live Twilio credentials and a public WSS backend URL.
- iOS code needs Xcode validation on macOS; this Linux VM cannot run `xcodebuild`.
