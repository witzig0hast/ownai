import type { Metadata, Viewport } from "next";
import { ArtifactPanel } from "@/components/ArtifactPanel";
import { AuthProvider } from "@/lib/auth-context";
import { ArtifactPanelProvider } from "@/lib/artifactPanel";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";

// Makes the app installable (Windows/Edge/Chrome "Install app", iPad Safari
// "Add to Home Screen") so it behaves like a standalone app rather than a
// browser tab — the chosen distribution path for PC and iPad (see root
// DECISIONS.md: no App Store, no Mac available for a native iPad build).
export const metadata: Metadata = {
  title: "OwnAI",
  description: "Personal AI assistant — chat, calendar and notification suggestions.",
  manifest: "/manifest.webmanifest",
  icons: {
    icon: [{ url: "/favicon-32.png", sizes: "32x32", type: "image/png" }],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  appleWebApp: {
    capable: true,
    title: "OwnAI",
    statusBarStyle: "black-translucent",
  },
};

export const viewport: Viewport = {
  themeColor: "#0f172a",
  width: "device-width",
  initialScale: 1,
  // Lets the layout extend under the notch/home indicator in the installed iOS app; NavBar and
  // AppShell pad with env(safe-area-inset-*) accordingly.
  viewportFit: "cover",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: THEME_INIT_SCRIPT adds the "dark" class before React hydrates.
    <html lang="de" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="flex h-full flex-col overflow-hidden font-sans">
        <AuthProvider>
          <ArtifactPanelProvider>
            {children}
            <ArtifactPanel />
          </ArtifactPanelProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
