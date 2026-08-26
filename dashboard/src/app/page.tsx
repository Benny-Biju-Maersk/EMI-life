import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { listThreads } from "@/lib/db";

export const dynamic = "force-dynamic"; // always read the latest SQLite state, never cache

export default function Home() {
  const threads = listThreads();

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <h1 className="mb-1 text-2xl font-semibold">FinBuddy — conversations</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        Internal view of WhatsApp threads, read directly from data/finbuddy.db.
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Threads ({threads.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {threads.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No conversations logged yet — message the WhatsApp bot to see them here.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>WhatsApp number</TableHead>
                  <TableHead>Messages</TableHead>
                  <TableHead>Last activity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {threads.map((t) => (
                  <TableRow key={t.threadId}>
                    <TableCell>
                      <Link
                        href={`/conversations/${encodeURIComponent(t.threadId)}`}
                        className="font-medium text-primary hover:underline"
                      >
                        {t.threadId}
                      </Link>
                    </TableCell>
                    <TableCell>{t.messageCount}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(t.lastActivity).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
