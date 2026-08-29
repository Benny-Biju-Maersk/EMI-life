"""Public API for web/ — the same tools/finance_tools.py logic every other
surface in this repo shares (Phase 1's REPL, Phase 2, the WhatsApp MVP),
exposed over plain JSON for a browser to call directly.

Deliberately a separate FastAPI app from whatsapp/webhook.py, not an
extra route bolted onto it: that file is Twilio-specific (TwiML replies,
webhook signature validation against TWILIO_AUTH_TOKEN) and named for that
job. This one serves a JavaScript frontend, and is where the auth-gated
profile/history endpoints web/ needs next will live — see
docs/product-brief.md's "Distribution" section (revised 2026-08-29) and
docs/multi-agent-patterns.md's tier-3-memory framing for why profile reads
are a separate concern from the stateless decode below.

Run with:
    uvicorn api.main:app --reload --port 8001

The /decode-offer endpoint is intentionally NOT behind auth — same
reasoning as the WhatsApp bot: the checkout-interception moment shouldn't
require an account to get a straight answer. Auth will gate the
save/recall-my-profile endpoints once those are built, not this one.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from tools.finance_tools import affordability_check, decode_emi_offer

app = FastAPI(title="FinBuddy public API")

# web/ runs on a different origin (localhost:3000 in dev) than this API
# (localhost:8001) — CORS has to be explicit or the browser blocks the
# request entirely. Tighten allow_origins to the real deployed domain
# before this goes anywhere past local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class DecodeOfferRequest(BaseModel):
    item_price: float
    tenure_months: int
    processing_fee: float = 0
    gst_on_fee_pct: float = 18.0
    forfeited_discount: float = 0
    stated_interest_pct: float = 0
    # Optional: when provided, the endpoint also returns an affordability
    # verdict, same as whatsapp/prompts.py's CHECKOUT_SYSTEM_PROMPT folding
    # affordability_check in when income is known.
    monthly_net_income: float | None = None
    existing_emis: float = 0


@app.post("/decode-offer")
def decode_offer(req: DecodeOfferRequest) -> dict:
    result = decode_emi_offer(
        req.item_price,
        req.tenure_months,
        req.processing_fee,
        req.gst_on_fee_pct,
        req.forfeited_discount,
        req.stated_interest_pct,
    )
    if "error" in result:
        return result

    if req.monthly_net_income is not None:
        result["affordability"] = affordability_check(
            req.monthly_net_income,
            req.existing_emis,
            req.item_price,
            tenure_months=req.tenure_months,
        )
    return result
