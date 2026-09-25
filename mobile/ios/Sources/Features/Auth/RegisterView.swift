import SwiftUI

struct RegisterView: View {
    @EnvironmentObject private var session: AuthSession
    @Environment(\.dismiss) private var dismiss

    @State private var displayName = ""
    @State private var email = ""
    @State private var password = ""
    @State private var isSubmitting = false

    private var canSubmit: Bool {
        !displayName.isEmpty && !email.isEmpty && password.count >= 8 && !isSubmitting
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Account") {
                    TextField("Display name", text: $displayName)
                        .textContentType(.name)
                    TextField("Email", text: $email)
                        .textContentType(.username)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Password (min. 8 characters)", text: $password)
                        .textContentType(.newPassword)
                }

                if let error = session.authError {
                    Section {
                        Text(error).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Create Account")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    if isSubmitting {
                        ProgressView()
                    } else {
                        Button("Sign Up", action: submit)
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
            await session.register(email: email, password: password, displayName: displayName)
            isSubmitting = false
            if session.isAuthenticated {
                dismiss()
            }
        }
    }
}

#Preview {
    RegisterView()
        .environmentObject(AuthSession())
}
