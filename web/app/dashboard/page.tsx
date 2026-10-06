import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { BudgetSnapshotWidget } from "./_components/BudgetSnapshotWidget";
import { ChatWidget } from "./_components/ChatWidget";
import { CouncilWidget } from "./_components/CouncilWidget";
import { DecodeOfferCard } from "./_components/DecodeOfferCard";
import { EmiCalculatorWidget } from "./_components/EmiCalculatorWidget";
import { ExpensesWidget } from "./_components/ExpensesWidget";
import { LoansWidget } from "./_components/LoansWidget";
import { MarketNewsWidget } from "./_components/MarketNewsWidget";
import { PersonalizedUpdatesWidget } from "./_components/PersonalizedUpdatesWidget";
import { ProfileWidget } from "./_components/ProfileWidget";
import { RemindersWidget } from "./_components/RemindersWidget";
import { StockQuoteWidget } from "./_components/StockQuoteWidget";

export const metadata = {
  title: "Dashboard — FinBuddy",
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";

export default async function DashboardPage() {
  // Every widget below that touches a specific person's data does so
  // through this app's own /api/* routes, which re-verify auth()
  // themselves server-side before calling api/main.py — this page-level
  // check is just so a signed-out visitor never sees the dashboard shell
  // at all, not the actual security boundary. See
  // app/api/profile/route.ts's comment.
  const { userId } = await auth();
  if (!userId) {
    redirect("/sign-in");
  }

  // First-run gate: every widget here assumes at least an income is
  // known (Budget Snapshot has nothing to compute otherwise) — send a
  // brand-new user through the onboarding questionnaire once, rather
  // than dropping them into a dashboard full of empty widgets asking the
  // same three questions independently.
  const profileRes = await fetch(`${API_URL}/profile?user_id=${encodeURIComponent(userId)}`, {
    cache: "no-store",
  });
  const profileData = await profileRes.json();
  const hasOnboarded = Boolean(profileData?.profile?.monthly_income);
  if (!hasOnboarded) {
    redirect("/onboarding");
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <h1 className="text-2xl font-semibold">Your FinBuddy portal</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Everything about your money, in one place — each widget below is
        one of FinBuddy&apos;s existing capabilities, not a mockup.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2">
        <div className="md:col-span-2">
          <ChatWidget />
        </div>
        <ProfileWidget />
        <BudgetSnapshotWidget />
        <LoansWidget />
        <ExpensesWidget />
        <PersonalizedUpdatesWidget />
        <DecodeOfferCard />
        <RemindersWidget />
        <EmiCalculatorWidget />
        <StockQuoteWidget />
        <MarketNewsWidget />
        <div className="md:col-span-2">
          <CouncilWidget />
        </div>
      </div>
    </div>
  );
}
