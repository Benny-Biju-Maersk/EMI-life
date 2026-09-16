import type { Metadata } from "next";
import { ClerkProvider, SignInButton, UserButton } from "@clerk/nextjs";
import { auth } from "@clerk/nextjs/server";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FinBuddy",
  description:
    "An unbiased gut-check before you take that checkout EMI. Decodes the real cost — hidden fees, forfeited discounts — before you commit.",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // @clerk/nextjs 7.x ("Core 3") removed the <SignedIn>/<SignedOut>
  // components entirely (they now throw at render time) — auth() from
  // '@clerk/nextjs/server' is the current way to branch on sign-in state
  // in a Server Component. See node_modules/@clerk/nextjs's
  // removedControlComponents.js if this ever needs re-checking against a
  // future Clerk version.
  const { userId } = await auth();

  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      >
        <body className="min-h-full flex flex-col">
          <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border bg-background/80 px-6 py-4 backdrop-blur-sm">
            <Link href="/" className="font-semibold tracking-tight">
              Fin<span className="text-primary">Buddy</span>
            </Link>
            <nav className="flex items-center gap-6 text-sm">
              <Link href="/decode" className="text-muted-foreground transition-colors hover:text-foreground">
                Decode an offer
              </Link>
              {userId && (
                <Link href="/dashboard" className="text-muted-foreground transition-colors hover:text-foreground">
                  Dashboard
                </Link>
              )}
              {userId ? (
                <UserButton />
              ) : (
                <SignInButton>
                  <button
                    type="button"
                    className="rounded-md bg-primary px-4 py-1.5 text-primary-foreground transition-colors hover:bg-primary/90"
                  >
                    Sign in
                  </button>
                </SignInButton>
              )}
            </nav>
          </header>
          <main className="flex-1">{children}</main>
        </body>
      </html>
    </ClerkProvider>
  );
}
