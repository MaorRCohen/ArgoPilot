import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { Atkinson_Hyperlegible_Next, Bricolage_Grotesque } from "next/font/google";
import { StatusLine } from "@/components/status-line";
import "./globals.css";

const display = Bricolage_Grotesque({ variable: "--font-display", subsets: ["latin"] });
const body = Atkinson_Hyperlegible_Next({ variable: "--font-body", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AgroPilot",
  description: "Should I water this plot today, and for how long?",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <header className="mx-auto w-full max-w-2xl px-4 pt-4">
          <Link href="/" className="font-heading text-lg font-bold tracking-tight">
            AgroPilot
          </Link>
        </header>
        <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-5">{children}</main>
        <footer className="mx-auto w-full max-w-2xl border-t px-4 py-3">
          <Suspense fallback={<p className="text-sm text-muted-foreground">Checking services…</p>}>
            <StatusLine />
          </Suspense>
        </footer>
      </body>
    </html>
  );
}
