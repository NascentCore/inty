//
//  LoginInitChatModel.swift
//  imate
//
//  Created by 天之行 on 2026/4/29.
//

import Foundation

struct ChatMessage: Identifiable {
    let id = UUID()
    let text: String
    let isUser: Bool
}

struct GenerateAvatarResponse: Decodable {
    let urls: [String]
}


// MARK: - Agent
struct AgentModel: Codable {

    let name: String
    let gender: String
    let avatar: String
    let background: String?
    let backgroundImages: [String]
    let backgroundAnimated: String?

    let voiceId: String?

    let settings: AgentSettings?

    let intro: String
    let statusLine: String?

    let opening: String
    let openingAudioUrl: String?

    let visibility: String
    let source: String

    let photos: [String]?
    let exclusivePhotos: [String]?

    let category: String?

    let prompt: String?
    let mainPrompt: String?
    let modePrompt: String?

    let personality: String?
    let scenario: String?
    let messageExample: String?

    let creatorNotes: String?
    let postHistoryInstructions: String?

    let alternateGreetings: [String]?

    let characterBook: String?

    let tags: [String]?

    let characterVersion: String?

    let extensions: String?

    let llmConfig: String?

    let metaData: String?

    let id: String
    let readableId: String

    let status: String

    let creatorId: String

    let createdAt: Int

    let updatedAt: Int?

    let deletedAt: Int?

    let version: Int

    let energyPoints: Int

    let isFollowed: Bool

    let followerCount: Int

    let connectorCount: Int

    let creator: CreatorModel

    let features: String?

    let avatarSize: String?

    let backgroundSize: String?

    enum CodingKeys: String, CodingKey {

        case name
        case gender
        case avatar
        case background

        case backgroundImages = "background_images"

        case backgroundAnimated = "background_animated"

        case voiceId = "voice_id"

        case settings

        case intro

        case statusLine = "status_line"

        case opening

        case openingAudioUrl = "opening_audio_url"

        case visibility

        case source

        case photos

        case exclusivePhotos = "exclusive_photos"

        case category

        case prompt

        case mainPrompt = "main_prompt"

        case modePrompt = "mode_prompt"

        case personality

        case scenario

        case messageExample = "message_example"

        case creatorNotes = "creator_notes"

        case postHistoryInstructions = "post_history_instructions"

        case alternateGreetings = "alternate_greetings"

        case characterBook = "character_book"

        case tags

        case characterVersion = "character_version"

        case extensions

        case llmConfig = "llm_config"

        case metaData = "meta_data"

        case id

        case readableId = "readable_id"

        case status

        case creatorId = "creator_id"

        case createdAt = "created_at"

        case updatedAt = "updated_at"

        case deletedAt = "deleted_at"

        case version

        case energyPoints = "energy_points"

        case isFollowed = "is_followed"

        case followerCount = "follower_count"

        case connectorCount = "connector_count"

        case creator

        case features

        case avatarSize = "avatar_size"

        case backgroundSize = "background_size"
    }
}

// MARK: - Settings

struct AgentSettings: Codable {

    let llmConfig: String?

    enum CodingKeys: String, CodingKey {

        case llmConfig = "llm_config"
    }
}

// MARK: - Creator

struct CreatorModel: Codable {

    let readableId: String

    let nickname: String

    let avatar: String?

    let email: String?

    let userPhoto: String?

    let phone: String?

    let gender: String?

    let ageGroup: String?

    let description: String?

    let systemLanguage: String

    let id: String

    let authType: String

    let isActive: Bool

    let createdAt: String

    let updatedAt: String?

    let isSuperuser: Bool

    let publicAgentsCount: Int

    let totalPublicAgentsFollows: Int

    let followersCount: Int

    let connectorCount: Int

    let actions: [String]

    enum CodingKeys: String, CodingKey {

        case readableId = "readable_id"

        case nickname

        case avatar

        case email

        case userPhoto = "user_photo"

        case phone

        case gender

        case ageGroup = "age_group"

        case description

        case systemLanguage = "system_language"

        case id

        case authType = "auth_type"

        case isActive = "is_active"

        case createdAt = "created_at"

        case updatedAt = "updated_at"

        case isSuperuser = "is_superuser"

        case publicAgentsCount = "public_agents_count"

        case totalPublicAgentsFollows = "total_public_agents_follows"

        case followersCount = "followers_count"

        case connectorCount = "connector_count"

        case actions
    }
}

