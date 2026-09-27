import type { Metadata, Viewport } from "next";
import { AuthProvider } from "@/lib/auth-context";
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
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col font-sans">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
