import SwiftUI

struct NewEventView: View {
    @ObservedObject var viewModel: CalendarViewModel
    @Environment(\.dismiss) private var dismiss

    @State private var title = ""
    @State private var start = Date()
    @State private var end = Date().addingTimeInterval(3600)
    @State private var location = ""
    @State private var isSubmitting = false

    private var canSubmit: Bool {
        !title.isEmpty && end > start && !isSubmitting
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Event") {
                    TextField("Title", text: $title)
                    DatePicker("Starts", selection: $start)
                    DatePicker("Ends", selection: $end)
                    TextField("Location (optional)", text: $location)
                }
            }
            .navigationTitle("New Event")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    if isSubmitting {
                        ProgressView()
                    } else {
                        Button("Save", action: submit)
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
            let success = await viewModel.createEvent(
                title: title,
                start: start,
                end: end,
                location: location.isEmpty ? nil : location
            )
            isSubmitting = false
            if success {
                dismiss()
            }
        }
    }
}

#Preview {
    NewEventView(viewModel: CalendarViewModel())
}
