# FOIR and loan affordability

FOIR (Fixed Obligation to Income Ratio) is the standard rule Indian banks
and NBFCs use to decide how much more EMI a borrower can safely take on.
It's the same rule `tools/finance_tools.py:affordability_check` implements
in code — this document is the plain-language explanation behind that
number, for when a user asks *why* a verdict came out the way it did.

**Formula:** FOIR % = (sum of all monthly EMIs, including the new one) /
monthly net (take-home) income × 100.

**Typical lender thresholds:**
- Below 40% FOIR: generally considered comfortable/safe.
- 40–50% FOIR: stretched — lenders may still approve but at higher
  scrutiny or a higher rate.
- Above 50% FOIR: not advisable — most lenders decline at this point, and
  even if approved, it leaves little room for an income shock or an
  emergency expense.

**Why it matters beyond loan approval:** a lender's threshold is a floor
for *their* risk, not necessarily a ceiling for the borrower's own
comfort. Someone with irregular income, no emergency fund, or other
near-term large expenses should treat 40% as a ceiling to stay well under,
not a target to reach.

**Common mistake this catches:** treating "the bank approved it" as proof
an EMI is affordable. Approval only means the *lender's* risk model
tolerates it — it says nothing about whether the borrower has slack left
for rent, essentials, or an emergency.
