import type { Metadata } from "next";
import { Suspense } from "react";
import { IBM_Plex_Sans, Unbounded } from "next/font/google";
import { MotionProvider } from "@/components/motion/provider";
import { StatusLine } from "@/components/status-line";
import { PHOTOS } from "@/lib/images";
import "./globals.css";

// Unbounded: a wide geometric sans for hero titles and headings (the extended, uppercase look of launch sites).
// IBM Plex Sans: clean, with tabular figures, for text and every number.
const heading = Unbounded({ variable: "--font-unbounded", subsets: ["latin"], display: "swap" });
const body = IBM_Plex_Sans({ variable: "--font-plex", subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "AgroPilot",
  description: "Should I water this plot today, and for how long?",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  const credits = PHOTOS.filter((p, i) => PHOTOS.findIndex((q) => q.credit === p.credit) === i);
  return (
    <html lang="en" className={`${heading.variable} ${body.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <MotionProvider>
          <div className="flex flex-1 flex-col">{children}</div>
          <footer className="on-dark bg-night">
            <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-3 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
              <Suspense fallback={<p className="text-sm text-muted-foreground">Checking services…</p>}>
                <StatusLine />
              </Suspense>
              <p className="text-sm text-muted-foreground">
                Photos on Unsplash by{" "}
                {credits.map((p, i) => (
                  <span key={p.credit}>
                    {i > 0 ? " and " : null}
                    <a
                      href={p.href}
                      target="_blank"
                      rel="noreferrer"
                      className="underline underline-offset-2 hover:text-foreground"
                    >
                      {p.credit}
                    </a>
                  </span>
                ))}
              </p>
            </div>
          </footer>
        </MotionProvider>
      </body>
    </html>
  );
}
