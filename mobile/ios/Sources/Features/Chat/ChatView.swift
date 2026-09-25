import SwiftUI

/// Sidebar (conversation list) + detail (message thread), which is the
/// natural shape for chat on iPad.
struct ChatView: View {
    @StateObject private var viewModel = ChatViewModel()
    @State private var columnVisibility: NavigationSplitViewVisibility = .all

    var body: some View {
        NavigationSplitView(columnVisibility: $columnVisibility) {
            conversationList
        } detail: {
            if let selectedID = viewModel.selectedConversationID {
                ChatDetailView(viewModel: viewModel, conversationID: selectedID)
            } else {
                ContentUnavailableView(
                    "No Conversation Selected",
                    systemImage: "bubble.left.and.bubble.right",
                    description: Text("Choose a conversation, or start a new one.")
                )
            }
        }
        .task {
            await viewModel.loadConversations()
        }
        .alert("Error", isPresented: errorBinding) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(viewModel.errorMessage ?? "")
        }
    }

    private var conversationList: some View {
        List(selection: $viewModel.selectedConversationID) {
            ForEach(viewModel.conversations) { conversation in
                VStack(alignment: .leading, spacing: 2) {
                    Text(conversation.title.isEmpty ? "Untitled" : conversation.title)
                        .font(.headline)
                        .lineLimit(1)
                    Text(conversation.updatedAt, style: .relative)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .tag(conversation.id)
            }
        }
        .navigationTitle("Chats")
        .overlay {
            if viewModel.isLoadingConversations && viewModel.conversations.isEmpty {
                ProgressView()
            } else if viewModel.conversations.isEmpty {
                ContentUnavailableView(
                    "No Chats Yet",
                    systemImage: "bubble.left.and.bubble.right",
                    description: Text("Tap + to start a conversation.")
                )
            }
        }
        .refreshable {
            await viewModel.loadConversations()
        }
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                LogoutToolbarButton()
            }
            ToolbarItem(placement: .primaryAction) {
                Button {
                    Task { await viewModel.createConversation() }
                } label: {
                    Label("New Chat", systemImage: "square.and.pencil")
                }
            }
        }
    }

    private var errorBinding: Binding<Bool> {
        Binding(
            get: { viewModel.errorMessage != nil },
            set: { isPresented in if !isPresented { viewModel.errorMessage = nil } }
        )
    }
}

#Preview {
    ChatView()
        .environmentObject(AuthSession())
}
