import SwiftUI

struct SuggestionsView: View {
    @StateObject private var viewModel = SuggestionsViewModel()

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.suggestions.isEmpty && !viewModel.isLoading {
                    ContentUnavailableView(
                        "No Open Suggestions",
                        systemImage: "sparkles",
                        description: Text("Suggestions generated from your Android device's notifications will show up here.")
                    )
                } else {
                    List(viewModel.suggestions) { suggestion in
                        SuggestionRow(
                            suggestion: suggestion,
                            isProcessing: viewModel.processingIDs.contains(suggestion.id),
                            onApply: { Task { await viewModel.apply(suggestion) } },
                            onDismiss: { Task { await viewModel.dismiss(suggestion) } }
                        )
                    }
                    .refreshable { await viewModel.load() }
                }
            }
            .overlay {
                if viewModel.isLoading && viewModel.suggestions.isEmpty {
                    ProgressView()
                }
            }
            .navigationTitle("Suggestions")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    LogoutToolbarButton()
                }
            }
            .alert("Error", isPresented: errorBinding) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(viewModel.errorMessage ?? "")
            }
        }
        .task {
            await viewModel.load()
        }
    }

    private var errorBinding: Binding<Bool> {
        Binding(
            get: { viewModel.errorMessage != nil },
            set: { isPresented in if !isPresented { viewModel.errorMessage = nil } }
        )
    }
}

private struct SuggestionRow: View {
    let suggestion: Suggestion
    let isProcessing: Bool
    let onApply: () -> Void
    let onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: suggestion.kind == .calendarEvent ? "calendar.badge.plus" : "text.bubble")
                    .foregroundStyle(Color.accentColor)
                Text(suggestion.summary)
                    .font(.headline)
            }

            Text(suggestion.createdAt, style: .relative)
                .font(.caption)
                .foregroundStyle(.secondary)

            if isProcessing {
                ProgressView()
                    .frame(maxWidth: .infinity)
            } else {
                HStack {
                    Button("Dismiss", role: .destructive, action: onDismiss)
                        .buttonStyle(.bordered)
                    Spacer()
                    Button("Apply", action: onApply)
                        .buttonStyle(.borderedProminent)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    SuggestionsView()
        .environmentObject(AuthSession())
}
