import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto max-w-2xl px-6 py-24 text-center">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
        An unbiased gut-check before you take that EMI.
      </h1>
      <p className="mt-6 text-lg leading-relaxed text-gray-600">
        &ldquo;No-cost EMI&rdquo; at checkout often isn&apos;t free. FinBuddy
        decodes the real cost — processing fees, forfeited discounts, the
        works — before you commit. No lender, no card network, no platform
        behind it. Just the numbers.
      </p>
      <div className="mt-10">
        <Link
          href="/decode"
          className="inline-block rounded-md bg-black px-8 py-3 text-white transition hover:bg-gray-800"
        >
          Decode an offer
        </Link>
      </div>
    </div>
  );
}
