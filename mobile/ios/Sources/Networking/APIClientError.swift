import Foundation

enum APIClientError: LocalizedError, Equatable {
    case invalidURL
    case networkError(String)
    case decodingError(String)
    /// A non-2xx response with the standard `{"error": {code, message}}` envelope.
    case server(code: String, message: String, status: Int)
    /// 401 that could not be resolved by refreshing the access token; the
    /// caller has been logged out.
    case unauthorized
    case unknown(status: Int)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid request URL."
        case .networkError(let description):
            return description
        case .decodingError:
            return "Could not read the server's response."
        case .server(_, let message, _):
            return message
        case .unauthorized:
            return "Your session has expired. Please log in again."
        case .unknown(let status):
            return "Unexpected server error (status \(status))."
        }
    }
}

extension Notification.Name {
    /// Posted when the app has been logged out because a token refresh
    /// failed. `AuthSession` observes this to reset its published state.
    static let ownAIDidLogout = Notification.Name("de.hastnetwork.ownai.didLogout")
}
