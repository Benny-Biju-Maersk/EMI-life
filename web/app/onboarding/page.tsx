import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import { OnboardingForm } from "./_components/OnboardingForm";

export const metadata = {
  title: "Set up — FinBuddy",
};

export default async function OnboardingPage() {
  const { userId } = await auth();
  if (!userId) {
    redirect("/sign-in");
  }
  return <OnboardingForm />;
}
