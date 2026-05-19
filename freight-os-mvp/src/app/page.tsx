import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { KanbanBoard } from "@/components/KanbanBoard";
import { StatusPill } from "@/components/StatusPill";
import { prisma } from "@/lib/db";
import Link from "next/link";
import { Sparkles, Package, TrendingUp, Clock } from "lucide-react";
import { format } from "date-fns";

export const dynamic = "force-dynamic";

async function getDashboardData() {
  const [shipments, totalCount, draftCount, transitCount, deliveredCount, recentAi] =
    await Promise.all([
      prisma.shipment.findMany({
        include: { customer: true, milestones: true },
        orderBy: { createdAt: "desc" },
        take: 50,
      }),
      prisma.shipment.count(),
      prisma.shipment.count({ where: { status: "DRAFT" } }),
      prisma.shipment.count({ where: { status: "IN_TRANSIT" } }),
      prisma.shipment.count({ where: { status: "DELIVERED" } }),
      prisma.aiLog.findMany({
        orderBy: { createdAt: "desc" },
        take: 5,
        include: { shipment: true },
      }),
    ]);
  return { shipments, totalCount, draftCount, transitCount, deliveredCount, recentAi };
}

export default async function HomePage() {
  const { shipments, totalCount, draftCount, transitCount, deliveredCount, recentAi } =
    await getDashboardData();

  return (
    <div className="flex">
      <Sidebar />
      <div className="flex-1 min-w-0">
        <Topbar title="Dashboard" />

        <main className="p-6 space-y-6">
          {/* KPI Strip */}
          <div className="grid grid-cols-4 gap-3">
            <KpiCard label="Total Shipments" value={totalCount} icon={Package} />
            <KpiCard label="Draft" value={draftCount} icon={Clock} accent="text-text-secondary" />
            <KpiCard label="In Transit" value={transitCount} icon={TrendingUp} accent="text-warning" />
            <KpiCard label="Delivered" value={deliveredCount} icon={Package} accent="text-success" />
          </div>

          {/* Action banner */}
          <Link href="/ai" className="block group">
            <div className="rounded-lg border border-border bg-gradient-to-br from-accent/10 via-bg-elevated to-bg-elevated p-5 hover:border-accent/40 transition">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
                  <Sparkles size={18} className="text-accent" />
                </div>
                <div className="flex-1">
                  <div className="font-medium">Parse a customer email with AI</div>
                  <div className="text-sm text-text-secondary">
                    Paste any inquiry email — auto-extract shipment details and create a draft in 5 seconds.
                  </div>
                </div>
                <div className="text-accent text-sm group-hover:translate-x-0.5 transition">
                  Try it →
                </div>
              </div>
            </div>
          </Link>

          {/* Workflow Kanban */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary">
                Workflow
              </h2>
              <Link href="/shipments" className="text-xs text-accent hover:underline">
                View all →
              </Link>
            </div>
            <KanbanBoard initial={shipments as any} />
          </section>

          {/* Recent AI activity */}
          <section>
            <h2 className="text-sm font-semibold uppercase tracking-wider text-text-secondary mb-3">
              Recent AI Activity
            </h2>
            <div className="border border-border rounded-lg bg-bg-elevated overflow-hidden">
              {recentAi.length === 0 && (
                <div className="p-6 text-center text-sm text-text-tertiary">
                  No AI activity yet. <Link href="/ai" className="text-accent">Try the parser</Link>.
                </div>
              )}
              {recentAi.map((log) => (
                <div
                  key={log.id}
                  className="px-4 py-2.5 border-b border-border last:border-0 flex items-center gap-3 hover:bg-bg-subtle"
                >
                  <Sparkles size={14} className="text-accent shrink-0" />
                  <span className="text-xs font-mono text-text-secondary">{log.agent}</span>
                  {log.shipment && (
                    <span className="text-xs font-mono text-accent">
                      {log.shipment.jobNo}
                    </span>
                  )}
                  {log.confidence && (
                    <span className={`pill ${
                      log.confidence === "high"
                        ? "bg-success/15 text-success"
                        : log.confidence === "medium"
                        ? "bg-warning/15 text-warning"
                        : "bg-danger/15 text-danger"
                    }`}>
                      {log.confidence}
                    </span>
                  )}
                  <div className="flex-1 text-sm text-text-secondary truncate">
                    {log.inputText.slice(0, 100)}...
                  </div>
                  <div className="text-xs text-text-tertiary shrink-0">
                    {format(log.createdAt, "HH:mm")}
                  </div>
                </div>
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  icon: Icon,
  accent = "text-text-primary",
}: {
  label: string;
  value: number;
  icon: any;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-bg-elevated p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-text-secondary">{label}</span>
        <Icon size={14} className="text-text-tertiary" />
      </div>
      <div className={`text-2xl font-semibold mt-1 ${accent}`}>{value}</div>
    </div>
  );
}
