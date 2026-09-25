import SwiftUI

struct ConnectCalDAVView: View {
    @ObservedObject var viewModel: CalendarViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var url = ""
    @State private var username = ""
    @State private var password = ""
    @State private var isSubmitting = false

    private var canSubmit: Bool {
        !url.isEmpty && !username.isEmpty && !password.isEmpty && !isSubmitting
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("CalDAV Server") {
                    TextField("Server URL", text: $url)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Password", text: $password)
                }

                Section {
                    Text("Credentials are sent to your OwnAI server and stored there encrypted (never in plaintext). They're used to sync events from your CalDAV calendar — Nextcloud, iCloud, or Google Calendar via CalDAV all work.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Connect CalDAV")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    if isSubmitting {
                        ProgressView()
                    } else {
                        Button("Connect", action: submit)
                            .disabled(!canSubmit)
                    }
                }
            }
        }
    }

    private func submit() {
        guard canSubmit else { return }
        isSubmitting = true
        Task {
            let success = await viewModel.connectCalDAV(url: url, username: username, password: password)
            isSubmitting = false
            if success {
                dismiss()
                await viewModel.loadEvents()
            }
        }
    }
}

#Preview {
    ConnectCalDAVView(viewModel: CalendarViewModel())
}
