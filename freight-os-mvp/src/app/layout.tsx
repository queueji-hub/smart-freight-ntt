import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Freight OS — AI-native Freight Forwarding",
  description: "The operating system for modern freight forwarders.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bg text-text-primary min-h-screen">{children}</body>
    </html>
  );
}
