"use client";

import { useEffect, useState } from "react";
import { Card, TextField } from "./shared";

type Reminder = {
  id: number;
  message: string;
  due_date: string;
  recurrence: string;
  last_sent_date: string | null;
};

export function RemindersWidget() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [message, setMessage] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [recurrence, setRecurrence] = useState<"none" | "monthly">("none");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  function load() {
    setLoading(true);
    fetch("/api/reminders")
      .then((r) => r.json())
      .then((data) => setReminders(data.reminders ?? []))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function create() {
    if (!message || !dueDate) return;
    setCreating(true);
    try {
      await fetch("/api/reminders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, due_date: dueDate, recurrence }),
      });
      setMessage("");
      setDueDate("");
      setRecurrence("none");
      load();
    } finally {
      setCreating(false);
    }
  }

  return (
    <Card title="My Reminders">
      <p className="text-xs text-muted-foreground">
        Delivered later, by a separate scheduled process — not by this page.
        See docs/multi-agent-patterns.md if you&apos;re curious why that
        split exists.
      </p>

      <div className="mt-2 space-y-2 text-sm">
        <TextField
          label="Remind me to…"
          value={message}
          onChange={setMessage}
          placeholder="Pay my personal loan EMI"
        />
        <div className="flex items-end gap-2">
          <label className="block flex-1">
            <span className="text-muted-foreground">Due date</span>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
            />
          </label>
          <label className="block">
            <span className="text-muted-foreground">Repeat</span>
            <select
              value={recurrence}
              onChange={(e) => setRecurrence(e.target.value as "none" | "monthly")}
              className="mt-1 rounded-md border border-border px-2 py-1"
            >
              <option value="none">Once</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>
        </div>
        <button
          type="button"
          onClick={create}
          disabled={creating || !message || !dueDate}
          className="w-full rounded-md bg-primary py-1.5 text-sm text-primary-foreground transition hover:bg-primary/90 disabled:opacity-50"
        >
          {creating ? "Saving…" : "Add reminder"}
        </button>
      </div>

      <div className="mt-4 border-t border-border pt-3">
        {loading ? (
          <p className="text-sm text-muted-foreground">Loading…</p>
        ) : reminders.length === 0 ? (
          <p className="text-sm text-muted-foreground/70">No reminders yet.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {reminders.map((r) => (
              <li key={r.id} className="flex justify-between">
                <span>{r.message}</span>
                <span className="text-muted-foreground">
                  {r.due_date}
                  {r.recurrence === "monthly" ? " · monthly" : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
