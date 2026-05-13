import AVFoundation
import Foundation

final class VoiceCallAudioEngine {
    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private var recorderConverter: AVAudioConverter?

    func start(onPcm16k: @escaping (Data) -> Void) throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker])
        try session.setActive(true)

        if player.engine == nil {
            engine.attach(player)
            let playbackFormat = AVAudioFormat(
                commonFormat: .pcmFormatInt16,
                sampleRate: 24_000,
                channels: 1,
                interleaved: true
            )!
            engine.connect(player, to: engine.mainMixerNode, format: playbackFormat)
        }

        let input = engine.inputNode
        let inputFormat = input.outputFormat(forBus: 0)
        let recordingFormat = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 16_000,
            channels: 1,
            interleaved: true
        )!
        recorderConverter = AVAudioConverter(from: inputFormat, to: recordingFormat)

        input.removeTap(onBus: 0)
        input.installTap(onBus: 0, bufferSize: 1024, format: inputFormat) { [weak self] buffer, _ in
            guard let self, let converter = self.recorderConverter else { return }
            let ratio = recordingFormat.sampleRate / inputFormat.sampleRate
            let capacity = AVAudioFrameCount(Double(buffer.frameLength) * ratio) + 1
            guard let outBuffer = AVAudioPCMBuffer(pcmFormat: recordingFormat, frameCapacity: capacity) else {
                return
            }
            var error: NSError?
            converter.convert(to: outBuffer, error: &error) { _, status in
                status.pointee = .haveData
                return buffer
            }
            guard error == nil else { return }
            let audioBuffer = outBuffer.audioBufferList.pointee.mBuffers
            guard let dataPointer = audioBuffer.mData, audioBuffer.mDataByteSize > 0 else { return }
            onPcm16k(Data(bytes: dataPointer, count: Int(audioBuffer.mDataByteSize)))
        }

        if !engine.isRunning {
            try engine.start()
        }
        if !player.isPlaying {
            player.play()
        }
    }

    func playPcm24k(_ data: Data) {
        guard let format = AVAudioFormat(
            commonFormat: .pcmFormatInt16,
            sampleRate: 24_000,
            channels: 1,
            interleaved: true
        ) else { return }
        let frames = AVAudioFrameCount(data.count / 2)
        guard let buffer = AVAudioPCMBuffer(pcmFormat: format, frameCapacity: frames) else { return }
        buffer.frameLength = frames
        let audioBuffer = buffer.audioBufferList.pointee.mBuffers
        guard let dst = audioBuffer.mData else { return }
        data.withUnsafeBytes { src in
            if let base = src.baseAddress {
                dst.copyMemory(from: base, byteCount: data.count)
            }
        }
        player.scheduleBuffer(buffer)
    }

    func stop() {
        engine.inputNode.removeTap(onBus: 0)
        player.stop()
        engine.stop()
        recorderConverter = nil
        try? AVAudioSession.sharedInstance().setActive(false)
    }
}
