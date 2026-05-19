import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Freight OS — Compact Console",
  description: "3-person freight forwarder ops console.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
