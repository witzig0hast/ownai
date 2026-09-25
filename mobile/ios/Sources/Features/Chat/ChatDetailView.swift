import SwiftUI

struct ChatDetailView: View {
    @ObservedObject var viewModel: ChatViewModel
    let conversationID: UUID

    @FocusState private var inputFocused: Bool

    private var title: String {
        viewModel.conversations.first(where: { $0.id == conversationID })?.title ?? "Chat"
    }

    var body: some View {
        VStack(spacing: 0) {
            messageList
            Divider()
            inputBar
        }
        .navigationTitle(title)
        .navigationBarTitleDisplayMode(.inline)
        .task(id: conversationID) {
            await viewModel.loadMessages(for: conversationID)
        }
    }

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    ForEach(viewModel.messages) { message in
                        MessageBubble(message: message)
                            .id(message.id)
                    }

                    if viewModel.isSending {
                        HStack(spacing: 8) {
                            ProgressView()
                            Text("OwnAI is thinking…")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        .id("sending-indicator")
                    }
                }
                .padding()
            }
            .onChange(of: viewModel.messages.count) {
                scrollToBottom(proxy)
            }
            .onChange(of: viewModel.isSending) {
                scrollToBottom(proxy)
            }
        }
        .overlay {
            if viewModel.isLoadingMessages && viewModel.messages.isEmpty {
                ProgressView()
            }
        }
    }

    private func scrollToBottom(_ proxy: ScrollViewProxy) {
        withAnimation {
            if viewModel.isSending {
                proxy.scrollTo("sending-indicator", anchor: .bottom)
            } else if let lastID = viewModel.messages.last?.id {
                proxy.scrollTo(lastID, anchor: .bottom)
            }
        }
    }

    private var inputBar: some View {
        HStack(alignment: .bottom, spacing: 8) {
            TextField("Message", text: $viewModel.draft, axis: .vertical)
                .lineLimit(1...5)
                .textFieldStyle(.roundedBorder)
                .focused($inputFocused)
                .disabled(viewModel.isSending)
                .onSubmit {
                    Task { await viewModel.sendMessage() }
                }

            Button {
                Task { await viewModel.sendMessage() }
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 30))
            }
            .disabled(viewModel.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || viewModel.isSending)
        }
        .padding()
    }
}

#Preview {
    NavigationStack {
        ChatDetailView(viewModel: ChatViewModel(), conversationID: UUID())
    }
}
