import SwiftUI

@main
struct OwnAIApp: App {
    @StateObject private var session = AuthSession()

    var body: some Scene {
        WindowGroup {
            Group {
                if session.isAuthenticated {
                    RootView()
                } else {
                    LoginView()
                }
            }
            .environmentObject(session)
        }
    }
}
