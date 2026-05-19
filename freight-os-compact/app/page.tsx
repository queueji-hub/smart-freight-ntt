"use client";
import { useState, useMemo } from "react";

type J = { id: number; c: string; pol: string; pod: string; s: string; f: number; n: string };
const S = ["Booking", "Customs", "Transit", "Delivered"] as const;
const SC: Record<string, string> = {
  Booking: "bg-zinc-500/15 text-zinc-300",
  Customs: "bg-amber-500/15 text-amber-400",
  Transit: "bg-blue-500/15 text-blue-400",
  Delivered: "bg-emerald-500/15 text-emerald-400",
};
const seed: J[] = [
  { id: 1, c: "Sunshine Supply Chain", pol: "LCH", pod: "SIN", s: "Transit", f: 78000, n: "ETD 12 May, SITC vessel" },
  { id: 2, c: "Leading Wheel Co.", pol: "Shanghai", pod: "LCH", s: "Customs", f: 145000, n: "Awaiting D/O from carrier" },
  { id: 3, c: "Thai Kronen Factory", pol: "BKK", pod: "MTY", s: "Booking", f: 92500, n: "AC flight TBA, +100K rate" },
  { id: 4, c: "Sunshine SCM", pol: "LCH", pod: "Bangkok", s: "Delivered", f: 56400, n: "POD signed by Akom 064-496-3956" },
];
const empty: J = { id: 0, c: "", pol: "", pod: "", s: "Booking", f: 0, n: "" };
const fmt = (n: number) => new Intl.NumberFormat("th-TH").format(n);

export default function Page() {
  const [jobs, setJobs] = useState<J[]>(seed);
  const [f, setF] = useState<J>(empty);
  const total = useMemo(() => jobs.filter(j => j.s !== "Delivered").reduce((a, b) => a + b.f, 0), [jobs]);
  const delivered = useMemo(() => jobs.filter(j => j.s === "Delivered").reduce((a, b) => a + b.f, 0), [jobs]);
  const u = (k: keyof J, v: any) => setF({ ...f, [k]: v });
  const save = () => {
    if (!f.c || !f.pol || !f.pod) return;
    if (f.id) setJobs(jobs.map(j => j.id === f.id ? f : j));
    else setJobs([...jobs, { ...f, id: Math.max(0, ...jobs.map(j => j.id)) + 1 }]);
    setF(empty);
  };
  const inp = "w-full bg-zinc-900 border border-zinc-800 rounded px-2.5 py-1.5 text-sm focus:border-zinc-600 outline-none";
  const lbl = "text-[10px] uppercase tracking-wider text-zinc-500 mb-1 block";

  return (
    <div className="min-h-screen bg-black text-zinc-100 font-sans">
      <header className="border-b border-zinc-900 px-6 py-3 flex items-center gap-3">
        <div className="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-xs font-bold">F</div>
        <span className="font-semibold text-sm">Freight OS</span>
        <span className="text-xs text-zinc-500 ml-2">3-person ops console</span>
        <div className="ml-auto flex gap-3 text-xs">
          <div><span className="text-zinc-500">Active </span><span className="text-emerald-400 font-mono">฿{fmt(total)}</span></div>
          <div><span className="text-zinc-500">Delivered </span><span className="text-zinc-300 font-mono">฿{fmt(delivered)}</span></div>
          <div><span className="text-zinc-500">Jobs </span><span className="text-zinc-100 font-mono">{jobs.length}</span></div>
        </div>
      </header>

      <main className="grid grid-cols-12 gap-0">
        <section className="col-span-4 border-r border-zinc-900 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs uppercase tracking-wider text-zinc-500">{f.id ? `Edit #${f.id}` : "New Job"}</h2>
            {f.id !== 0 && <button onClick={() => setF(empty)} className="text-[10px] text-zinc-500 hover:text-zinc-300">Clear</button>}
          </div>
          <div className="space-y-2.5">
            <div><label className={lbl}>Customer</label><input className={inp} value={f.c} onChange={e => u("c", e.target.value)} placeholder="Sunshine SCM" /></div>
            <div className="grid grid-cols-2 gap-2">
              <div><label className={lbl}>POL</label><input className={inp} value={f.pol} onChange={e => u("pol", e.target.value)} placeholder="LCH" /></div>
              <div><label className={lbl}>POD</label><input className={inp} value={f.pod} onChange={e => u("pod", e.target.value)} placeholder="SIN" /></div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={lbl}>Status</label>
                <select className={inp} value={f.s} onChange={e => u("s", e.target.value)}>
                  {S.map(x => <option key={x}>{x}</option>)}
                </select>
              </div>
              <div><label className={lbl}>Fee (THB)</label><input type="number" className={inp} value={f.f || ""} onChange={e => u("f", +e.target.value)} placeholder="0" /></div>
            </div>
            <div><label className={lbl}>Internal Notes</label><textarea className={inp + " h-20 resize-none"} value={f.n} onChange={e => u("n", e.target.value)} placeholder="Vessel info, contact, blockers..." /></div>
            <button onClick={save} className="w-full bg-indigo-500 hover:bg-indigo-400 rounded py-1.5 text-sm font-medium transition">{f.id ? "Save Changes" : "+ Create Job"}</button>
          </div>
        </section>

        <section className="col-span-8 p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs uppercase tracking-wider text-zinc-500">Active Shipments</h2>
            <span className="text-[10px] text-zinc-600">Click row → edit instantly</span>
          </div>
          <div className="border border-zinc-900 rounded overflow-hidden">
            <div className="grid grid-cols-12 px-3 py-2 text-[10px] uppercase tracking-wider text-zinc-500 bg-zinc-950 border-b border-zinc-900">
              <div className="col-span-1">#</div>
              <div className="col-span-3">Customer</div>
              <div className="col-span-2">Route</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-2 text-right">Fee</div>
              <div className="col-span-2">Notes</div>
            </div>
            {jobs.map(j => (
              <div key={j.id} onClick={() => setF(j)} className={`grid grid-cols-12 px-3 py-2.5 text-sm border-b border-zinc-900 last:border-0 cursor-pointer transition ${f.id === j.id ? "bg-indigo-500/10" : "hover:bg-zinc-900/50"}`}>
                <div className="col-span-1 font-mono text-xs text-zinc-500">{String(j.id).padStart(3, "0")}</div>
                <div className="col-span-3 truncate">{j.c}</div>
                <div className="col-span-2 font-mono text-xs text-zinc-400">{j.pol} → {j.pod}</div>
                <div className="col-span-2"><span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${SC[j.s]}`}>{j.s}</span></div>
                <div className="col-span-2 text-right font-mono text-xs">฿{fmt(j.f)}</div>
                <div className="col-span-2 text-xs text-zinc-500 truncate">{j.n || "—"}</div>
              </div>
            ))}
            {jobs.length === 0 && <div className="px-3 py-8 text-center text-sm text-zinc-600">No active jobs</div>}
          </div>

          <div className="mt-4 grid grid-cols-4 gap-2">
            {S.map(s => {
              const c = jobs.filter(j => j.s === s).length;
              return (
                <div key={s} className="border border-zinc-900 rounded px-3 py-2">
                  <div className="text-[10px] uppercase tracking-wider text-zinc-500">{s}</div>
                  <div className="text-lg font-semibold mt-0.5">{c}</div>
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
