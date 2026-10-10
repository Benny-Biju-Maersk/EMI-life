import Link from "next/link";
import { Hero3DLoader } from "./_components/Hero3DLoader";

export default function Home() {
  return (
    <div className="relative overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-40 h-80 bg-gradient-to-b from-primary/10 to-transparent blur-2xl"
      />
      <div className="relative mx-auto grid max-w-5xl grid-cols-1 items-center gap-4 px-6 py-16 sm:py-24 md:grid-cols-2 md:gap-8">
        <div className="text-center md:text-left">
          <span className="inline-block rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted-foreground">
            No lender behind this. No platform behind this.
          </span>
          <h1 className="mt-6 text-4xl font-bold tracking-tight sm:text-5xl">
            An unbiased gut-check before you take that EMI.
          </h1>
          <p className="mt-6 text-lg leading-relaxed text-muted-foreground">
            &ldquo;No-cost EMI&rdquo; at checkout often isn&apos;t free.
            FinBuddy decodes the real cost — processing fees, forfeited
            discounts, the works — before you commit. Just the numbers.
          </p>
          <div className="mt-10 flex items-center justify-center gap-3 md:justify-start">
            <Link
              href="/decode"
              className="inline-block rounded-md bg-primary px-8 py-3 font-medium text-primary-foreground transition hover:bg-primary/90"
            >
              Decode an offer
            </Link>
            <Link
              href="/dashboard"
              className="inline-block rounded-md border border-border px-8 py-3 font-medium transition hover:bg-card"
            >
              Open my portal
            </Link>
          </div>
        </div>

        <div>
          <Hero3DLoader />
          <p className="-mt-2 text-center text-xs text-muted-foreground/70 md:text-left">
            Drag it. It&apos;s not just a picture.
          </p>
        </div>
      </div>
    </div>
  );
}
