import SwiftUI

/// Top-level navigation once logged in: Chat / Calendar / Suggestions.
///
/// A `TabView` is used at this level (rather than folding everything into
/// one `NavigationSplitView`) because each tab has its own natural
/// navigation shape — Chat wants a sidebar+detail split, Calendar and
/// Suggestions are simple stacks — and `TabView` composes cleanly with both
/// on iPadOS 17+.
struct RootView: View {
    var body: some View {
        TabView {
            ChatView()
                .tabItem { Label("Chat", systemImage: "bubble.left.and.bubble.right") }

            CalendarView()
                .tabItem { Label("Calendar", systemImage: "calendar") }

            SuggestionsView()
                .tabItem { Label("Suggestions", systemImage: "sparkles") }
        }
    }
}

/// Shared toolbar button used on each tab's root screen.
struct LogoutToolbarButton: View {
    @EnvironmentObject private var session: AuthSession

    var body: some View {
        Button(role: .destructive) {
            session.logout()
        } label: {
            Label("Log Out", systemImage: "rectangle.portrait.and.arrow.right")
        }
    }
}

#Preview {
    RootView()
        .environmentObject(AuthSession())
}
