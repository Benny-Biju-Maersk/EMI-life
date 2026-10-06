# What "no-cost EMI" actually hides

"No-cost EMI" / "zero-cost EMI" at checkout (Amazon, Flipkart, a card's EMI
conversion, or BNPL apps like Simpl/LazyPay) means the *stated interest
rate* is 0% — not that the offer is free. `tools/finance_tools.py:decode_emi_offer`
computes the real, effective cost; this document explains where that cost
usually comes from, for when a user wants the plain-language version.

**The two most common hidden costs:**

1. **Processing/convenience fee.** Often 1–3% of the item price (or a flat
   fee), charged upfront, usually with 18% GST added on top of the fee
   itself — not on the item. A ₹50,000 phone with a ₹999 processing fee
   plus 18% GST on that fee adds roughly ₹1,179 the "0% interest" heading
   doesn't mention.
2. **A forfeited instant discount or cashback.** Many checkout offers show
   a discount ("₹2,000 off") or cashback that's only available when paying
   in full — choosing EMI silently forfeits it. That forfeited amount is a
   real cost of choosing EMI, even though no interest was ever charged.

**How to spot which one applies:** read the fine print for "processing
fee," "convenience fee," or "applicable only on full payment" language
near the discount. If a fee or a forfeited discount exists, the offer
isn't actually free — it's interest hidden as a fee or a lost discount,
not a literal 0%.

**When a "no-cost EMI" claim is genuinely true:** if there is no
processing fee and no discount forfeited by choosing EMI, the claim can be
accurate — the merchant/bank is absorbing the cost as a promotion. This is
less common than the two hidden-cost patterns above, but does happen.
