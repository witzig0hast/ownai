import Foundation

// MARK: - Requests

struct RegisterRequest: Encodable {
    let email: String
    let password: String
    let displayName: String

    enum CodingKeys: String, CodingKey {
        case email, password
        case displayName = "display_name"
    }
}

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct RefreshRequest: Encodable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

struct CreateConversationRequest: Encodable {
    let title: String?
}

struct SendMessageRequest: Encodable {
    let content: String
}

struct ConnectCalDAVRequest: Encodable {
    let url: String
    let username: String
    let password: String
}

struct CreateEventRequest: Encodable {
    let title: String
    let start: Date
    let end: Date
    let location: String?
}

// MARK: - Responses

struct ConversationsResponse: Decodable {
    let conversations: [Conversation]
}

struct MessagesResponse: Decodable {
    let messages: [ChatMessage]
}

struct SendMessageResponse: Decodable {
    let message: ChatMessage
}

struct ConnectCalDAVResponse: Decodable {
    let connected: Bool
}

struct EventsResponse: Decodable {
    let events: [CalendarEvent]
}

struct SuggestionsResponse: Decodable {
    let suggestions: [Suggestion]
}

struct DismissSuggestionResponse: Decodable {
    let status: String
}

/// The error envelope every non-2xx response uses, per API.md:
/// `{ "error": { "code": "...", "message": "..." } }`
struct APIErrorEnvelope: Decodable {
    struct Detail: Decodable {
        let code: String
        let message: String
    }

    let error: Detail
}
