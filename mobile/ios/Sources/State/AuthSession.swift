import Foundation

/// The app's single source of truth for "am I logged in", shared via
/// `.environmentObject` from `OwnAIApp`.
@MainActor
final class AuthSession: ObservableObject {
    @Published private(set) var isAuthenticated: Bool
    @Published private(set) var currentUser: User?
    @Published var authError: String?

    private let api = APIClient.shared

    init() {
        isAuthenticated = KeychainStore.shared.accessToken != nil

        NotificationCenter.default.addObserver(
            forName: .ownAIDidLogout,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.handleForcedLogout()
        }

        if isAuthenticated {
            Task { await loadCurrentUser() }
        }
    }

    func login(email: String, password: String) async {
        authError = nil
        do {
            let tokens = try await api.login(email: email, password: password)
            KeychainStore.shared.saveTokens(tokens)
            isAuthenticated = true
            await loadCurrentUser()
        } catch {
            authError = message(for: error)
        }
    }

    func register(email: String, password: String, displayName: String) async {
        authError = nil
        do {
            _ = try await api.register(email: email, password: password, displayName: displayName)
            await login(email: email, password: password)
        } catch {
            authError = message(for: error)
        }
    }

    func logout() {
        KeychainStore.shared.clearTokens()
        currentUser = nil
        isAuthenticated = false
    }

    private func handleForcedLogout() {
        currentUser = nil
        isAuthenticated = false
        authError = "Your session has expired. Please log in again."
    }

    private func loadCurrentUser() async {
        currentUser = try? await api.currentUser()
    }

    private func message(for error: Error) -> String {
        (error as? LocalizedError)?.errorDescription ?? "Something went wrong. Please try again."
    }
}
