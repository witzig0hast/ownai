import Foundation

@MainActor
final class ChatViewModel: ObservableObject {
    @Published var conversations: [Conversation] = []
    @Published var selectedConversationID: UUID?
    @Published var messages: [ChatMessage] = []
    @Published var draft: String = ""

    @Published var isLoadingConversations = false
    @Published var isLoadingMessages = false
    @Published var isSending = false
    @Published var errorMessage: String?

    private let api = APIClient.shared

    func loadConversations() async {
        isLoadingConversations = true
        defer { isLoadingConversations = false }
        do {
            let loaded = try await api.conversations().sorted { $0.updatedAt > $1.updatedAt }
            conversations = loaded
            if selectedConversationID == nil {
                selectedConversationID = loaded.first?.id
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func createConversation() async {
        do {
            let conversation = try await api.createConversation(title: nil)
            conversations.insert(conversation, at: 0)
            selectedConversationID = conversation.id
            messages = []
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadMessages(for conversationID: UUID) async {
        isLoadingMessages = true
        defer { isLoadingMessages = false }
        do {
            messages = try await api.messages(conversationID: conversationID)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    /// Sends `draft`, then reloads the full thread. The POST endpoint only
    /// returns the assistant's reply (API.md), so re-fetching the thread is
    /// the simplest correct way to also pick up the persisted user message
    /// — the request is synchronous, so by the time it returns both
    /// messages are already stored server-side.
    func sendMessage() async {
        guard let conversationID = selectedConversationID else { return }
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        draft = ""
        isSending = true
        defer { isSending = false }

        do {
            try await api.sendMessage(conversationID: conversationID, content: text)
            messages = try await api.messages(conversationID: conversationID)
            if let index = conversations.firstIndex(where: { $0.id == conversationID }) {
                let updated = conversations.remove(at: index)
                conversations.insert(updated, at: 0)
            }
        } catch {
            errorMessage = error.localizedDescription
            draft = text
        }
    }
}
