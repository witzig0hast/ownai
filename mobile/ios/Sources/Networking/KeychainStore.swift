import Foundation
import Security

/// Minimal Keychain-backed storage for the access and refresh tokens.
///
/// Tokens must never live in `UserDefaults` (plist on disk, unencrypted).
/// The Keychain is the standard, Apple-recommended place for credentials.
final class KeychainStore: @unchecked Sendable {
    static let shared = KeychainStore()

    private let service = "de.hastnetwork.ownai.auth"
    private let accessTokenAccount = "accessToken"
    private let refreshTokenAccount = "refreshToken"

    private init() {}

    var accessToken: String? {
        read(account: accessTokenAccount)
    }

    var refreshToken: String? {
        read(account: refreshTokenAccount)
    }

    func saveTokens(accessToken: String, refreshToken: String) {
        save(accessToken, account: accessTokenAccount)
        save(refreshToken, account: refreshTokenAccount)
    }

    func saveTokens(_ tokens: AuthTokens) {
        saveTokens(accessToken: tokens.accessToken, refreshToken: tokens.refreshToken)
    }

    func clearTokens() {
        delete(account: accessTokenAccount)
        delete(account: refreshTokenAccount)
    }

    // MARK: - Low-level Keychain access

    private func save(_ value: String, account: String) {
        let data = Data(value.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        // Upsert: remove any existing item first, then add the fresh one.
        SecItemDelete(query as CFDictionary)

        var attributes = query
        attributes[kSecValueData as String] = data
        attributes[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        SecItemAdd(attributes as CFDictionary, nil)
    }

    private func read(account: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private func delete(account: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
    }
}
