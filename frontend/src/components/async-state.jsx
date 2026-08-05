import { AlertCircle, FileSearch, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function PageLoadingState({ label = "Loading" }) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-200 bg-white/70 p-8" aria-live="polite">
      <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
      <p className="text-sm text-slate-500">{label}</p>
    </div>
  );
}

export function InlineErrorState({ title = "Something went wrong", message, onRetry }) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-xl border border-red-200 bg-red-50/70 p-8 text-center" role="alert">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 text-red-600"><AlertCircle className="h-5 w-5" /></div>
      <div><h2 className="font-semibold text-red-950">{title}</h2><p className="mt-1 max-w-md text-sm text-red-700">{message || "Please try again."}</p></div>
      {onRetry && <Button type="button" variant="outline" onClick={onRetry}>Try again</Button>}
    </div>
  );
}

export function EmptyState({ title, message, action }) {
  return (
    <div className="flex min-h-52 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-200 bg-slate-50/70 p-8 text-center">
      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white text-slate-500 shadow-sm"><FileSearch className="h-5 w-5" /></div>
      <div><h2 className="font-semibold text-slate-900">{title}</h2><p className="mt-1 max-w-md text-sm text-slate-500">{message}</p></div>
      {action}
    </div>
  );
}
