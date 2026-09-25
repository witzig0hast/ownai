import Foundation

@MainActor
final class SuggestionsViewModel: ObservableObject {
    @Published var suggestions: [Suggestion] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var processingIDs: Set<UUID> = []

    private let api = APIClient.shared

    func load() async {
        isLoading = true
        defer { isLoading = false }
        do {
            suggestions = try await api.suggestions(status: "open")
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func apply(_ suggestion: Suggestion) async {
        processingIDs.insert(suggestion.id)
        defer { processingIDs.remove(suggestion.id) }
        do {
            try await api.applySuggestion(id: suggestion.id)
            suggestions.removeAll { $0.id == suggestion.id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func dismiss(_ suggestion: Suggestion) async {
        processingIDs.insert(suggestion.id)
        defer { processingIDs.remove(suggestion.id) }
        do {
            try await api.dismissSuggestion(id: suggestion.id)
            suggestions.removeAll { $0.id == suggestion.id }
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}
