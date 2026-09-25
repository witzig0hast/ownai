import Foundation

/// A small `URLSession`-based client for the OwnAI backend, matching
/// `API.md` exactly. No third-party networking dependency is needed.
///
/// Auth: the access token (15 min TTL) is attached as a `Bearer` header on
/// every authenticated call. On a `401`, the client transparently attempts
/// one refresh (via `RefreshCoordinator`, so concurrent 401s only trigger a
/// single `/auth/refresh` call) and retries the original request once. If
/// the refresh itself fails, tokens are cleared and `.ownAIDidLogout` is
/// posted so the UI can return to the login screen.
final class APIClient: @unchecked Sendable {
    static let shared = APIClient()

    private enum Auth {
        case none
        case bearer
    }

    private let session: URLSession
    private let baseURL: URL
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    private let refreshCoordinator = RefreshCoordinator()

    private init() {
        baseURL = AppConfig.apiBaseURL

        let configuration = URLSessionConfiguration.default
        // Chat replies are synchronous and may involve one or more tool
        // calls on the backend (calendar lookups, etc.), so give those a
        // generous timeout compared to the default 60s.
        configuration.timeoutIntervalForRequest = 120
        configuration.timeoutIntervalForResource = 180
        session = URLSession(configuration: configuration)

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom { dateDecoder in
            let container = try dateDecoder.singleValueContainer()
            let string = try container.decode(String.self)
            if let date = APIClient.iso8601Fractional.date(from: string) {
                return date
            }
            if let date = APIClient.iso8601.date(from: string) {
                return date
            }
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "Invalid ISO-8601 date: \(string)")
        }
        self.decoder = decoder

        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .custom { date, dateEncoder in
            var container = dateEncoder.singleValueContainer()
            try container.encode(APIClient.iso8601.string(from: date))
        }
        self.encoder = encoder
    }

    private static let iso8601: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()

    private static let iso8601Fractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    // MARK: - Auth

    func register(email: String, password: String, displayName: String) async throws -> User {
        let body = try encoder.encode(RegisterRequest(email: email, password: password, displayName: displayName))
        let request = try makeRequest(path: "/auth/register", method: "POST", bodyData: body, auth: .none)
        return try await perform(request, auth: .none)
    }

    func login(email: String, password: String) async throws -> AuthTokens {
        let body = try encoder.encode(LoginRequest(email: email, password: password))
        let request = try makeRequest(path: "/auth/login", method: "POST", bodyData: body, auth: .none)
        return try await perform(request, auth: .none)
    }

    /// Used only by `RefreshCoordinator`.
    func performRefresh(refreshToken: String) async throws -> AuthTokens {
        let body = try encoder.encode(RefreshRequest(refreshToken: refreshToken))
        let request = try makeRequest(path: "/auth/refresh", method: "POST", bodyData: body, auth: .none)
        return try await perform(request, auth: .none, allowRefreshRetry: false)
    }

    func currentUser() async throws -> User {
        let request = try makeRequest(path: "/users/me", method: "GET", auth: .bearer)
        return try await perform(request, auth: .bearer)
    }

    // MARK: - Chat

    func conversations() async throws -> [Conversation] {
        let request = try makeRequest(path: "/chat/conversations", method: "GET", auth: .bearer)
        let response: ConversationsResponse = try await perform(request, auth: .bearer)
        return response.conversations
    }

    func createConversation(title: String? = nil) async throws -> Conversation {
        let body = try encoder.encode(CreateConversationRequest(title: title))
        let request = try makeRequest(path: "/chat/conversations", method: "POST", bodyData: body, auth: .bearer)
        return try await perform(request, auth: .bearer)
    }

    func messages(conversationID: UUID) async throws -> [ChatMessage] {
        let request = try makeRequest(path: "/chat/conversations/\(conversationID.uuidString.lowercased())/messages", method: "GET", auth: .bearer)
        let response: MessagesResponse = try await perform(request, auth: .bearer)
        return response.messages
    }

    /// Synchronous per API.md: this suspends until the assistant's full
    /// reply (including any tool calls) is ready. No streaming in v1.
    @discardableResult
    func sendMessage(conversationID: UUID, content: String) async throws -> ChatMessage {
        let body = try encoder.encode(SendMessageRequest(content: content))
        let request = try makeRequest(path: "/chat/conversations/\(conversationID.uuidString.lowercased())/messages", method: "POST", bodyData: body, auth: .bearer)
        let response: SendMessageResponse = try await perform(request, auth: .bearer)
        return response.message
    }

    // MARK: - Calendar

    func connectCalDAV(url: String, username: String, password: String) async throws -> Bool {
        let body = try encoder.encode(ConnectCalDAVRequest(url: url, username: username, password: password))
        let request = try makeRequest(path: "/integrations/caldav", method: "POST", bodyData: body, auth: .bearer)
        let response: ConnectCalDAVResponse = try await perform(request, auth: .bearer)
        return response.connected
    }

    func events(start: Date, end: Date) async throws -> [CalendarEvent] {
        let query = [
            URLQueryItem(name: "start", value: Self.iso8601.string(from: start)),
            URLQueryItem(name: "end", value: Self.iso8601.string(from: end))
        ]
        let request = try makeRequest(path: "/calendar/events", method: "GET", query: query, auth: .bearer)
        let response: EventsResponse = try await perform(request, auth: .bearer)
        return response.events
    }

    func createEvent(title: String, start: Date, end: Date, location: String?) async throws -> CalendarEvent {
        let body = try encoder.encode(CreateEventRequest(title: title, start: start, end: end, location: location))
        let request = try makeRequest(path: "/calendar/events", method: "POST", bodyData: body, auth: .bearer)
        return try await perform(request, auth: .bearer)
    }

    // MARK: - Notification suggestions

    func suggestions(status: String = "open") async throws -> [Suggestion] {
        let query = [URLQueryItem(name: "status", value: status)]
        let request = try makeRequest(path: "/notifications/suggestions", method: "GET", query: query, auth: .bearer)
        let response: SuggestionsResponse = try await perform(request, auth: .bearer)
        return response.suggestions
    }

    @discardableResult
    func applySuggestion(id: UUID) async throws -> Suggestion {
        let request = try makeRequest(path: "/notifications/suggestions/\(id.uuidString.lowercased())/apply", method: "POST", auth: .bearer)
        return try await perform(request, auth: .bearer)
    }

    @discardableResult
    func dismissSuggestion(id: UUID) async throws -> String {
        let request = try makeRequest(path: "/notifications/suggestions/\(id.uuidString.lowercased())/dismiss", method: "POST", auth: .bearer)
        let response: DismissSuggestionResponse = try await perform(request, auth: .bearer)
        return response.status
    }

    // MARK: - Request building

    private func makeRequest(path: String, method: String, query: [URLQueryItem] = [], bodyData: Data? = nil, auth: Auth) throws -> URLRequest {
        guard var components = URLComponents(string: baseURL.absoluteString + path) else {
            throw APIClientError.invalidURL
        }
        if !query.isEmpty {
            components.queryItems = query
        }
        guard let url = components.url else {
            throw APIClientError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if case .bearer = auth, let token = KeychainStore.shared.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        if let bodyData {
            request.httpBody = bodyData
        }

        return request
    }

    // MARK: - Request execution

    private func perform<T: Decodable>(_ request: URLRequest, auth: Auth, allowRefreshRetry: Bool = true) async throws -> T {
        let (data, response) = try await execute(request)

        guard let http = response as? HTTPURLResponse else {
            throw APIClientError.unknown(status: -1)
        }

        if (200..<300).contains(http.statusCode) {
            do {
                return try decoder.decode(T.self, from: data)
            } catch {
                throw APIClientError.decodingError(String(describing: error))
            }
        }

        if http.statusCode == 401, case .bearer = auth, allowRefreshRetry {
            do {
                _ = try await refreshCoordinator.refresh(using: self)
            } catch {
                forceLogout()
                throw APIClientError.unauthorized
            }

            var retryRequest = request
            if let token = KeychainStore.shared.accessToken {
                retryRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
            return try await perform(retryRequest, auth: auth, allowRefreshRetry: false)
        }

        if http.statusCode == 401 {
            if case .bearer = auth {
                forceLogout()
            }
            throw APIClientError.unauthorized
        }

        if let envelope = try? decoder.decode(APIErrorEnvelope.self, from: data) {
            throw APIClientError.server(code: envelope.error.code, message: envelope.error.message, status: http.statusCode)
        }
        throw APIClientError.unknown(status: http.statusCode)
    }

    private func execute(_ request: URLRequest) async throws -> (Data, URLResponse) {
        do {
            return try await session.data(for: request)
        } catch {
            throw APIClientError.networkError(error.localizedDescription)
        }
    }

    private func forceLogout() {
        KeychainStore.shared.clearTokens()
        NotificationCenter.default.post(name: .ownAIDidLogout, object: nil)
    }
}
