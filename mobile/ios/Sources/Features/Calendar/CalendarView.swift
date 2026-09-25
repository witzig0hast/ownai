import SwiftUI

struct CalendarView: View {
    @StateObject private var viewModel = CalendarViewModel()
    @State private var showConnectSheet = false
    @State private var showNewEventSheet = false

    var body: some View {
        NavigationStack {
            Group {
                if viewModel.events.isEmpty && !viewModel.isLoading {
                    ContentUnavailableView(
                        "No Events",
                        systemImage: "calendar",
                        description: Text("Connect CalDAV or create an event to get started.")
                    )
                } else {
                    List(viewModel.events) { event in
                        EventRow(event: event)
                    }
                    .refreshable { await viewModel.loadEvents() }
                }
            }
            .overlay {
                if viewModel.isLoading && viewModel.events.isEmpty {
                    ProgressView()
                }
            }
            .navigationTitle("Calendar")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    LogoutToolbarButton()
                }
                ToolbarItem(placement: .primaryAction) {
                    Menu {
                        Button {
                            showNewEventSheet = true
                        } label: {
                            Label("New Event", systemImage: "plus")
                        }
                        Button {
                            showConnectSheet = true
                        } label: {
                            Label("Connect CalDAV", systemImage: "link")
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }
                }
            }
            .sheet(isPresented: $showConnectSheet) {
                ConnectCalDAVView(viewModel: viewModel)
            }
            .sheet(isPresented: $showNewEventSheet) {
                NewEventView(viewModel: viewModel)
            }
            .alert("Error", isPresented: errorBinding) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(viewModel.errorMessage ?? "")
            }
        }
        .task {
            await viewModel.loadEvents()
        }
    }

    private var errorBinding: Binding<Bool> {
        Binding(
            get: { viewModel.errorMessage != nil },
            set: { isPresented in if !isPresented { viewModel.errorMessage = nil } }
        )
    }
}

private struct EventRow: View {
    let event: CalendarEvent

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(event.title)
                .font(.headline)

            HStack(spacing: 4) {
                Text(event.start, format: .dateTime.day().month().year().hour().minute())
                Text("–")
                Text(event.end, format: .dateTime.hour().minute())
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)

            if let location = event.location, !location.isEmpty {
                Label(location, systemImage: "mappin.and.ellipse")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 2)
    }
}

#Preview {
    CalendarView()
        .environmentObject(AuthSession())
}
