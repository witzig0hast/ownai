import Foundation

/// App-wide configuration.
///
/// The default points at a backend forwarded to `localhost` (e.g. via
/// `ssh -L 8000:localhost:8000 ...`, a simulator running against a Mac-local
/// backend, or Xcode's "Debug > Attach to Process" style port forwarding).
///
/// ## Pointing at a real server
///
/// To use this against your actual OwnAI server (e.g. over Tailscale or a
/// LAN IP), do one of the following:
///
/// 1. **Quickest for local testing**: edit `fallbackBaseURL` below, e.g.
///    `http://192.168.1.50:8000/api/v1` or `https://ownai.example.com/api/v1`.
/// 2. **No source edits**: add an `OWNAI_API_BASE_URL` environment variable
///    to your Xcode scheme (Product > Scheme > Edit Scheme… > Run >
///    Arguments > Environment Variables) set to the full base URL including
///    `/api/v1`. This overrides the fallback at launch, which is convenient
///    for switching between a local and a remote backend without editing code.
///
/// If the server is reachable only over plain HTTP (no TLS) and is **not**
/// `localhost`, iOS's App Transport Security will block the request unless
/// the host is on a private/local network — see the `NSAppTransportSecurity`
/// notes in `project.yml` and in `README.md` ("HTTP during local development").
enum AppConfig {
    /// The default base URL used when no `OWNAI_API_BASE_URL` environment
    /// variable is set. Already includes the `/api/v1` prefix.
    static let fallbackBaseURL = "http://localhost:8000/api/v1"

    /// The effective API base URL for this run of the app.
    static var apiBaseURL: URL {
        if let override = ProcessInfo.processInfo.environment["OWNAI_API_BASE_URL"],
           let url = URL(string: override) {
            return url
        }
        guard let url = URL(string: fallbackBaseURL) else {
            preconditionFailure("AppConfig.fallbackBaseURL is not a valid URL: \(fallbackBaseURL)")
        }
        return url
    }
}
