import Foundation

/// Ensures at most one `/auth/refresh` request is in flight at a time.
///
/// Without this, several requests that all hit a 401 around the same time
/// (e.g. the conversation list and the message list loading together) would
/// each try to refresh the access token independently, racing to persist
/// tokens and likely invalidating one another's refresh token.
actor RefreshCoordinator {
    private var inFlightTask: Task<AuthTokens, Error>?

    /// Performs the refresh, or awaits an already-running one.
    func refresh(using client: APIClient) async throws -> AuthTokens {
        if let inFlightTask {
            return try await inFlightTask.value
        }

        let task = Task<AuthTokens, Error> {
            guard let refreshToken = KeychainStore.shared.refreshToken else {
                throw APIClientError.unauthorized
            }
            let tokens = try await client.performRefresh(refreshToken: refreshToken)
            KeychainStore.shared.saveTokens(tokens)
            return tokens
        }
        inFlightTask = task

        do {
            let result = try await task.value
            inFlightTask = nil
            return result
        } catch {
            inFlightTask = nil
            throw error
        }
    }
}
