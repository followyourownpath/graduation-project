import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const tones = {
  default: "bg-slate-100 text-slate-600",
  info: "bg-blue-50 text-blue-600",
  warning: "bg-amber-50 text-amber-600",
  danger: "bg-red-50 text-red-600",
  success: "bg-emerald-50 text-emerald-600",
};

export function MetricCard({ label, value, hint, icon: Icon, tone = "default" }) {
  return (
    <Card className="rounded-xl border-slate-200 shadow-sm">
      <CardContent className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div><p className="text-sm font-medium text-slate-600">{label}</p><p className="mt-3 text-3xl font-semibold tracking-tight tabular-nums text-slate-950">{value}</p></div>
          <div className={cn("flex h-9 w-9 items-center justify-center rounded-lg", tones[tone])}>{Icon && <Icon className="h-4 w-4" />}</div>
        </div>
        <p className="mt-3 text-xs text-slate-500">{hint}</p>
      </CardContent>
    </Card>
  );
}
