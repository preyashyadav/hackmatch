import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HackMatch — Find your co-founder",
  description: "AI-powered matchmaking for hackathon attendees",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased">
        {children}
      </body>
    </html>
  );
}
