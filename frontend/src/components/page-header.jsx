import { cn } from "@/lib/utils";

export function PageHeader({ eyebrow, title, description, actions, className }) {
  return (
    <div className={cn("flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0">
        {eyebrow && <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-blue-700">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap items-center gap-2 [&>*]:max-sm:flex-1">{actions}</div>}
    </div>
  );
}
