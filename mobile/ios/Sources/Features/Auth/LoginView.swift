import SwiftUI

struct LoginView: View {
    @EnvironmentObject private var session: AuthSession

    @State private var email = ""
    @State private var password = ""
    @State private var isSubmitting = false
    @State private var showRegister = false

    private var canSubmit: Bool {
        !email.isEmpty && !password.isEmpty && !isSubmitting
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                Spacer()

                VStack(spacing: 6) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 44))
                        .foregroundStyle(Color.accentColor)
                    Text("OwnAI")
                        .font(.largeTitle.bold())
                    Text("Your self-hosted assistant")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                VStack(spacing: 12) {
                    TextField("Email", text: $email)
                        .textContentType(.username)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textFieldStyle(.roundedBorder)

                    SecureField("Password", text: $password)
                        .textContentType(.password)
                        .textFieldStyle(.roundedBorder)
                        .onSubmit(submit)
                }
                .padding(.horizontal)

                if let error = session.authError {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }

                Button(action: submit) {
                    if isSubmitting {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                    } else {
                        Text("Log In")
                            .frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(!canSubmit)
                .padding(.horizontal)

                Button("Create an account") {
                    showRegister = true
                }
                .font(.footnote)

                Spacer()
                Spacer()
            }
            .padding()
            .sheet(isPresented: $showRegister) {
                RegisterView()
            }
        }
    }

    private func submit() {
        guard canSubmit else { return }
        isSubmitting = true
        Task {
            await session.login(email: email, password: password)
            isSubmitting = false
        }
    }
}

#Preview {
    LoginView()
        .environmentObject(AuthSession())
}
