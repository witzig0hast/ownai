import Foundation

// MARK: - Auth

struct User: Codable, Identifiable {
    let id: UUID
    let email: String
    let displayName: String
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, email
        case displayName = "display_name"
        case createdAt = "created_at"
    }
}

struct AuthTokens: Codable {
    let accessToken: String
    let refreshToken: String
    let tokenType: String
    let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case expiresIn = "expires_in"
    }
}

// MARK: - Chat

struct Conversation: Codable, Identifiable {
    let id: UUID
    let title: String?
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id, title
        case updatedAt = "updated_at"
    }
}

struct ChatMessage: Codable, Identifiable {
    enum Role: String, Codable, Equatable {
        case user, assistant, tool
    }

    let id: UUID
    let role: Role
    let content: String
    let toolCalls: [ToolCall]?
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id, role, content
        case toolCalls = "tool_calls"
        case createdAt = "created_at"
    }
}

struct ToolCall: Codable {
    let tool: String
    let arguments: [String: AnyCodable]
    let result: [String: AnyCodable]?
}

// MARK: - Calendar

struct CalendarEvent: Codable, Identifiable {
    /// Note: unlike other resources in the API, event ids are plain strings
    /// (they may originate from an external CalDAV server), not UUIDs.
    let id: String
    let title: String
    let start: Date
    let end: Date
    let location: String?
    let source: String
}

// MARK: - Notification suggestions

struct Suggestion: Codable, Identifiable {
    enum Kind: String, Codable, Equatable {
        case calendarEvent = "calendar_event"
        case replyDraft = "reply_draft"
    }

    enum Status: String, Codable, Equatable {
        case open, applied, dismissed
    }

    let id: UUID
    let notificationId: UUID
    let kind: Kind
    let summary: String
    let payload: [String: AnyCodable]
    let status: Status
    let createdAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case notificationId = "notification_id"
        case kind, summary, payload, status
        case createdAt = "created_at"
    }
}
