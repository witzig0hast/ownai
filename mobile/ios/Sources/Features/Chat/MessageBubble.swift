import SwiftUI

struct MessageBubble: View {
    let message: ChatMessage

    private var isUser: Bool { message.role == .user }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 40) }

            VStack(alignment: isUser ? .trailing : .leading, spacing: 6) {
                if let toolCalls = message.toolCalls, !toolCalls.isEmpty {
                    ForEach(Array(toolCalls.enumerated()), id: \.offset) { _, call in
                        Label(call.tool, systemImage: "wrench.and.screwdriver")
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(.thinMaterial, in: Capsule())
                    }
                }

                if !message.content.isEmpty {
                    Text(message.content)
                        .padding(10)
                        .background(isUser ? Color.accentColor : Color.gray.opacity(0.18))
                        .foregroundStyle(isUser ? Color.white : Color.primary)
                        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                }
            }

            if !isUser { Spacer(minLength: 40) }
        }
    }
}

#Preview {
    VStack(spacing: 12) {
        MessageBubble(message: ChatMessage(
            id: UUID(),
            role: .user,
            content: "What's on my calendar today?",
            toolCalls: nil,
            createdAt: Date()
        ))
        MessageBubble(message: ChatMessage(
            id: UUID(),
            role: .assistant,
            content: "You have one event: Team sync at 15:00.",
            toolCalls: [ToolCall(tool: "calendar.list_events", arguments: [:], result: nil)],
            createdAt: Date()
        ))
    }
    .padding()
}
