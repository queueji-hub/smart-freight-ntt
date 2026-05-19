"use client";
import { Check } from "lucide-react";
import clsx from "clsx";
import { format } from "date-fns";

type Milestone = {
  id: string;
  code: string;
  name: string;
  occurredAt: string | null;
  note: string | null;
  sortOrder: number;
};

export function Timeline({ milestones }: { milestones: Milestone[] }) {
  const sorted = [...milestones].sort((a, b) => a.sortOrder - b.sortOrder);
  const lastDoneIdx = sorted.map((m) => !!m.occurredAt).lastIndexOf(true);
  const nextIdx = lastDoneIdx + 1;

  return (
    <div className="relative pl-2">
      {sorted.map((m, i) => {
        const done = !!m.occurredAt;
        const current = !done && i === nextIdx;
        const last = i === sorted.length - 1;

        return (
          <div key={m.id} className="relative flex gap-4 pb-5">
            {!last && (
              <div
                className={clsx(
                  "absolute left-[11px] top-6 w-0.5 h-full",
                  done ? "bg-success/40" : "bg-border"
                )}
              />
            )}
            <div
              className={clsx(
                "relative w-6 h-6 rounded-full flex items-center justify-center z-10 border-2 shrink-0",
                done && "bg-success border-success",
                current && "bg-warning border-warning animate-pulse-soft",
                !done && !current && "bg-bg-elevated border-border"
              )}
            >
              {done && <Check size={12} strokeWidth={3} className="text-white" />}
            </div>
            <div className="flex-1 -mt-0.5">
              <div className="flex items-baseline gap-2">
                <span className={clsx("text-sm font-medium",
                  !done && !current && "text-text-tertiary"
                )}>
                  {m.name}
                </span>
                <span className="text-[10px] text-text-tertiary font-mono">
                  {m.code}
                </span>
              </div>
              {done && m.occurredAt && (
                <div className="text-xs text-success mt-0.5">
                  ✓ {format(new Date(m.occurredAt), "dd MMM yyyy, HH:mm")}
                </div>
              )}
              {current && (
                <div className="text-xs text-warning mt-0.5">In progress</div>
              )}
              {!done && !current && (
                <div className="text-xs text-text-tertiary mt-0.5">Pending</div>
              )}
              {m.note && (
                <div className="text-xs text-text-secondary mt-1">{m.note}</div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
