import { clerkMiddleware } from "@clerk/nextjs/server";

// Next.js renamed the "middleware" file convention to "proxy" (this repo's
// installed version already deprecates the old name) — clerkMiddleware()'s
// returned function is still the right shape, just under a new filename
// and export name. See node_modules/next/dist/docs/.../proxy.md.
//
// Clerk's recommended matcher: run on every route except static assets,
// always run on API routes. See https://clerk.com/docs/references/nextjs/clerk-middleware
export default clerkMiddleware();

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
