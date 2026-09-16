// Small shared pieces every widget card uses — kept here once rather than
// each widget reimplementing its own Field/Row/Card, since a portal with
// many widgets is exactly the case where that duplication adds up fast.

export function Card({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-5 shadow-sm transition-shadow hover:shadow-md">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="text-muted-foreground">{label}</span>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
      />
    </label>
  );
}

export function TextField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="text-muted-foreground">{label}</span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="mt-1 w-full rounded-md border border-border bg-background px-2 py-1.5 outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/20"
      />
    </label>
  );
}

export function Row({ label, value }: { label: string; value?: number | string }) {
  if (value === undefined || value === null) return null;
  const display = typeof value === "number" ? `₹${value.toLocaleString("en-IN")}` : value;
  return (
    <div className="flex justify-between">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{display}</dd>
    </div>
  );
}

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8001";
