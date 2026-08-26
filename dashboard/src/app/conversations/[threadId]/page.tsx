import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { getThreadMessages, getThreadToolCalls } from "@/lib/db";

export const dynamic = "force-dynamic";

type TimelineEntry =
  | { kind: "message"; createdAt: string; role: string; content: string }
  | {
      kind: "tool_call";
      createdAt: string;
      toolName: string;
      toolInput: string;
      toolOutput: string;
    };

function verdictBadge(toolOutput: string) {
  try {
    const parsed = JSON.parse(toolOutput);
    if (typeof parsed?.verdict === "string") {
      const negative = /not_advisable|has hidden cost|stretched/i.test(parsed.verdict);
      return (
        <Badge variant={negative ? "destructive" : "secondary"}>
          {parsed.verdict}
        </Badge>
      );
    }
  } catch {
    // tool_output wasn't JSON (shouldn't normally happen — every tool in
    // tools/finance_tools.py returns json.dumps(...)) — just skip the badge.
  }
  return null;
}

export default async function ThreadPage({
  params,
}: {
  params: Promise<{ threadId: string }>;
}) {
  const { threadId: rawThreadId } = await params;
  const threadId = decodeURIComponent(rawThreadId);

  const messages = getThreadMessages(threadId);
  const toolCalls = getThreadToolCalls(threadId);

  if (messages.length === 0 && toolCalls.length === 0) {
    notFound();
  }

  const timeline: TimelineEntry[] = [
    ...messages.map(
      (m): TimelineEntry => ({
        kind: "message",
        createdAt: m.createdAt,
        role: m.role,
        content: m.content,
      })
    ),
    ...toolCalls.map(
      (t): TimelineEntry => ({
        kind: "tool_call",
        createdAt: t.createdAt,
        toolName: t.toolName,
        toolInput: t.toolInput,
        toolOutput: t.toolOutput,
      })
    ),
  ].sort((a, b) => a.createdAt.localeCompare(b.createdAt));

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Link href="/" className="text-sm text-muted-foreground hover:underline">
        ← All threads
      </Link>
      <h1 className="mt-2 mb-6 text-2xl font-semibold">{threadId}</h1>

      <div className="flex flex-col gap-3">
        {timeline.map((entry, i) =>
          entry.kind === "message" ? (
            <Card
              key={i}
              className={entry.role === "user" ? "border-primary/30" : ""}
            >
              <CardContent className="flex items-start justify-between gap-4">
                <div>
                  <Badge variant={entry.role === "user" ? "default" : "outline"}>
                    {entry.role}
                  </Badge>
                  <p className="mt-2 whitespace-pre-wrap text-sm">{entry.content}</p>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {new Date(entry.createdAt).toLocaleTimeString()}
                </span>
              </CardContent>
            </Card>
          ) : (
            <Card key={i} className="bg-muted/40">
              <CardContent>
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">tool</Badge>
                    <span className="font-mono text-sm">{entry.toolName}</span>
                    {verdictBadge(entry.toolOutput)}
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {new Date(entry.createdAt).toLocaleTimeString()}
                  </span>
                </div>
                <pre className="mt-2 overflow-x-auto rounded bg-background p-2 text-xs">
                  in: {entry.toolInput}
                  {"\n"}
                  out: {entry.toolOutput}
                </pre>
              </CardContent>
            </Card>
          )
        )}
      </div>
    </main>
  );
}
