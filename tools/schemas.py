"""Tool schemas in Anthropic tool-use format.

The description fields matter a lot — the model decides *when* to call a
tool based on them. Treat them as prompts, not documentation.
"""

TOOL_SCHEMAS = [
    {
        "name": "calculate_emi",
        "description": (
            "Calculate the monthly EMI, total interest, and total payment for a loan "
            "using the standard reducing-balance formula. Use whenever the user asks "
            "about EMI amounts, loan costs, or 'what will I pay per month'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "principal": {"type": "number", "description": "Loan amount in INR"},
                "annual_rate_pct": {"type": "number", "description": "Annual interest rate in percent, e.g. 10.5"},
                "tenure_months": {"type": "integer", "description": "Loan tenure in months"},
            },
            "required": ["principal", "annual_rate_pct", "tenure_months"],
        },
    },
    {
        "name": "prepayment_impact",
        "description": (
            "Estimate how much tenure and interest a one-time loan prepayment saves, "
            "keeping the EMI constant. Use when the user asks whether to prepay a loan "
            "or what a lumpsum payment would save them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "principal": {"type": "number", "description": "Original loan amount in INR"},
                "annual_rate_pct": {"type": "number"},
                "tenure_months": {"type": "integer"},
                "months_paid": {"type": "integer", "description": "EMIs already paid"},
                "lumpsum": {"type": "number", "description": "One-time prepayment amount in INR"},
            },
            "required": ["principal", "annual_rate_pct", "tenure_months", "months_paid", "lumpsum"],
        },
    },
    {
        "name": "affordability_check",
        "description": (
            "Rule-based verdict on whether the user can afford a purchase, using the "
            "FOIR (fixed obligation to income ratio) rule lenders use. Use whenever the "
            "user asks 'can I afford X' or 'should I buy X on EMI'. Ask the user for "
            "their monthly net income and existing EMIs first if you don't know them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "monthly_net_income": {"type": "number", "description": "Take-home income per month in INR"},
                "existing_emis": {"type": "number", "description": "Sum of current monthly EMIs in INR, 0 if none"},
                "purchase_price": {"type": "number"},
                "down_payment": {"type": "number", "description": "Upfront payment, default 0"},
                "annual_rate_pct": {"type": "number", "description": "Expected loan rate, default 15 for consumer loans"},
                "tenure_months": {"type": "integer", "description": "Planned tenure, default 12"},
                "monthly_essential_expenses": {"type": "number", "description": "Rent, food, utilities etc. Optional but improves the verdict."},
            },
            "required": ["monthly_net_income", "existing_emis", "purchase_price"],
        },
    },
    {
        "name": "decode_emi_offer",
        "description": (
            "Decode what a checkout 'no-cost EMI' or BNPL offer actually costs, "
            "beyond the advertised zero-interest sticker. Use whenever the user is "
            "facing (or forwards a screenshot of) a checkout EMI offer and asks "
            "'is this really free', 'should I take this EMI', or similar. If you "
            "can see or infer a processing fee or a discount/cashback that's only "
            "available on full payment, pass them in — don't guess a number the "
            "offer doesn't state; ask the user instead if it matters and isn't shown."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "item_price": {"type": "number", "description": "Sticker price of the item in INR"},
                "tenure_months": {"type": "integer", "description": "EMI tenure in months"},
                "processing_fee": {"type": "number", "description": "Processing/convenience fee before GST, in INR. 0 if none stated."},
                "gst_on_fee_pct": {"type": "number", "description": "GST rate applied to the processing fee, default 18"},
                "forfeited_discount": {"type": "number", "description": "Instant discount or cashback only available on full payment, forfeited by choosing EMI. 0 if none."},
                "stated_interest_pct": {"type": "number", "description": "Stated annual interest rate if this isn't actually a 'no cost' offer, default 0"},
            },
            "required": ["item_price", "tenure_months"],
        },
    },
    {
        "name": "get_stock_quote",
        "description": (
            "Fetch a recent stock quote (price, day range, 52-week range). "
            "For NSE stocks append .NS to the symbol (RELIANCE.NS, TCS.NS); "
            "for BSE append .BO. Use for any question about a current stock price."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol with exchange suffix, e.g. INFY.NS"},
            },
            "required": ["symbol"],
        },
    },
]
