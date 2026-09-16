import Link from "next/link";
import { Card } from "./shared";

// The full decode tool already exists as its own page (app/decode) — no
// need to duplicate that form here, just point at it.
export function DecodeOfferCard() {
  return (
    <Card title="Decode a Checkout EMI Offer">
      <p className="text-sm text-muted-foreground">
        Forward a &ldquo;no-cost EMI&rdquo; offer&apos;s terms and see the
        real cost — processing fees, forfeited discounts, the works.
      </p>
      <Link
        href="/decode"
        className="mt-3 inline-block rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90"
      >
        Open the decoder →
      </Link>
    </Card>
  );
}
