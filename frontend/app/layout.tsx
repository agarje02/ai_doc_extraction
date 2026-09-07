import type { Metadata } from "next";
import Link from "next/link";
import { API_BASE } from "@/lib/api";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Document Intelligence",
  description: "Extract structured entities from unstructured documents.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-(--border) bg-(--surface)">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-(--accent) font-bold text-[#0b0f17]">
                AI
              </span>
              <span className="text-lg font-semibold">
                Document Intelligence
              </span>
            </Link>
            <nav className="flex items-center gap-4 text-sm text-(--muted)">
              <Link href="/" className="hover:text-(--text)">
                Documents
              </Link>
              <a
                href={`${API_BASE}/docs`}
                target="_blank"
                rel="noreferrer"
                className="hover:text-(--text)"
              >
                API
              </a>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
