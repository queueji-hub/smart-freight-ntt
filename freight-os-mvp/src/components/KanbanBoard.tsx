"use client";
import { useState } from "react";
import { StatusPill } from "./StatusPill";
import clsx from "clsx";

type Shipment = {
  id: string;
  jobNo: string;
  jobType: string;
  status: string;
  carrier: string | null;
  pol: string | null;
  pod: string | null;
  customer: { companyName: string } | null;
};

const COLUMNS = [
  { key: "DRAFT", label: "Draft", color: "border-text-tertiary/40" },
  { key: "BOOKED", label: "Booked", color: "border-accent/60" },
  { key: "IN_TRANSIT", label: "In Transit", color: "border-warning/60" },
  { key: "DELIVERED", label: "Delivered", color: "border-success/60" },
];

export function KanbanBoard({ initial }: { initial: Shipment[] }) {
  const [items, setItems] = useState(initial);
  const [dragId, setDragId] = useState<string | null>(null);

  const onDrop = async (status: string) => {
    if (!dragId) return;
    const card = items.find((i) => i.id === dragId);
    if (!card || card.status === status) return;

    setItems((prev) => prev.map((i) => (i.id === dragId ? { ...i, status } : i)));
    setDragId(null);

    await fetch(`/api/shipments/${dragId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
  };

  return (
    <div className="grid grid-cols-4 gap-3">
      {COLUMNS.map((col) => {
        const cards = items.filter((i) => i.status === col.key);
        return (
          <div
            key={col.key}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => onDrop(col.key)}
            className={clsx(
              "rounded-lg border-t-2 bg-bg-elevated/50 p-2 min-h-[400px]",
              col.color
            )}
          >
            <div className="flex items-center justify-between px-2 py-1 mb-2">
              <span className="text-xs font-medium uppercase tracking-wider text-text-secondary">
                {col.label}
              </span>
              <span className="text-xs text-text-tertiary">{cards.length}</span>
            </div>
            <div className="space-y-1.5">
              {cards.map((c) => (
                <div
                  key={c.id}
                  draggable
                  onDragStart={() => setDragId(c.id)}
                  className="bg-bg-elevated border border-border rounded-md p-2.5 cursor-grab active:cursor-grabbing hover:border-border-strong transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-mono text-[11px] text-accent">{c.jobNo}</span>
                    <StatusPill status={c.status} />
                  </div>
                  <div className="text-sm font-medium truncate">
                    {c.customer?.companyName || "—"}
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">
                    {c.pol || "?"} → {c.pod || "?"}
                  </div>
                  {c.carrier && (
                    <div className="text-[10px] text-text-tertiary mt-1">
                      {c.carrier}
                    </div>
                  )}
                </div>
              ))}
              {cards.length === 0 && (
                <div className="text-xs text-text-tertiary text-center py-4">
                  Drop here
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
