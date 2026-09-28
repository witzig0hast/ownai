export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="animate-fade-in-up mb-5">
      <h1 className="text-xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-100">{title}</h1>
      {subtitle ? <p className="mt-1.5 text-sm text-zinc-500">{subtitle}</p> : null}
    </div>
  );
}
