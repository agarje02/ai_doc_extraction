import type { Metadata } from "next";
import Link from "next/link";
import ThemeToggle from "./theme-toggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Document Intelligence",
  description: "Extract structured entities from unstructured documents.",
};

// Applied before paint to avoid a flash of the wrong theme.
// Light is the default; only an explicit user choice switches to dark.
const themeInitScript = `
(function () {
  try {
    var stored = localStorage.getItem('theme');
    var theme = stored === 'dark' ? 'dark' : 'light';
    document.documentElement.dataset.theme = theme;
  } catch (e) {
    document.documentElement.dataset.theme = 'light';
  }
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body>
        <header className="sticky top-0 z-20 border-b border-(--border) bg-(--surface)/80 shadow-(--shadow) backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="grid h-9 w-9 place-items-center rounded-xl bg-(--accent) font-bold text-(--accent-foreground) shadow-(--shadow)">
                AI
              </span>
              <span className="text-lg font-semibold tracking-tight">
                Document Intelligence
              </span>
            </Link>
            <nav className="flex items-center gap-2 text-sm">
              <Link
                href="/"
                className="rounded-lg px-3 py-1.5 text-(--muted) transition-colors hover:bg-(--surface-2) hover:text-(--text)"
              >
                Documents
              </Link>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
