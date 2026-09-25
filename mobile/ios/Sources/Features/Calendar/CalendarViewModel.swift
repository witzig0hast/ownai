import Foundation

@MainActor
final class CalendarViewModel: ObservableObject {
    @Published var events: [CalendarEvent] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    /// Local-only hint (there is no "am I connected" GET endpoint in
    /// API.md); reflects the result of the last successful `connectCalDAV`
    /// call in this app session.
    @Published var isCalDAVConnected = false

    private let api = APIClient.shared

    /// Loads a window of events around `referenceDate`: one month back to
    /// two months forward, which comfortably covers "what's coming up"
    /// without the client having to page through the whole calendar.
    func loadEvents(referenceDate: Date = Date()) async {
        isLoading = true
        defer { isLoading = false }

        let calendar = Calendar.current
        let start = calendar.date(byAdding: .month, value: -1, to: referenceDate) ?? referenceDate
        let end = calendar.date(byAdding: .month, value: 2, to: referenceDate) ?? referenceDate

        do {
            events = try await api.events(start: start, end: end).sorted { $0.start < $1.start }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func connectCalDAV(url: String, username: String, password: String) async -> Bool {
        do {
            let connected = try await api.connectCalDAV(url: url, username: username, password: password)
            isCalDAVConnected = connected
            return connected
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }

    func createEvent(title: String, start: Date, end: Date, location: String?) async -> Bool {
        do {
            let event = try await api.createEvent(title: title, start: start, end: end, location: location)
            events.append(event)
            events.sort { $0.start < $1.start }
            return true
        } catch {
            errorMessage = error.localizedDescription
            return false
        }
    }
}
