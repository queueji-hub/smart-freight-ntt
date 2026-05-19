"use client";
import { Search, Sparkles, Command } from "lucide-react";
import { useState, useEffect } from "react";

export function CommandBar() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-bg-subtle border border-border hover:border-border-strong text-sm text-text-secondary w-72 transition-colors"
      >
        <Search size={14} />
        <span className="flex-1 text-left">Search shipments, customers...</span>
        <kbd className="px-1.5 py-0.5 rounded bg-bg-elevated border border-border text-[10px] flex items-center gap-0.5">
          <Command size={10} /> K
        </kbd>
      </button>

      {/* Modal */}
      {open && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-center pt-32"
          onClick={() => setOpen(false)}
        >
          <div
            className="w-[640px] max-w-[90vw] bg-bg-elevated border border-border-strong rounded-lg shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
              <Sparkles size={16} className="text-accent" />
              <input
                autoFocus
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search jobs, containers, customers, or ask AI..."
                className="flex-1 bg-transparent outline-none text-sm placeholder:text-text-tertiary"
              />
              <kbd className="text-[10px] text-text-tertiary px-1.5 py-0.5 rounded bg-bg-subtle">
                ESC
              </kbd>
            </div>

            <div className="p-2 max-h-96 overflow-auto">
              {!query && (
                <>
                  <div className="px-2 pt-2 pb-1 text-[10px] uppercase tracking-wider text-text-tertiary">
                    Quick actions
                  </div>
                  <ResultRow
                    icon="✨"
                    title="Parse customer email with AI"
                    href="/ai"
                  />
                  <ResultRow
                    icon="📦"
                    title="View all shipments"
                    href="/shipments"
                  />
                  <ResultRow icon="🏠" title="Open dashboard" href="/" />
                </>
              )}
              {query && (
                <div className="p-3 text-sm text-text-secondary">
                  Searching for <span className="text-text-primary">"{query}"</span>...
                  <div className="text-xs text-text-tertiary mt-1">
                    (Live search wiring in progress — go to Shipments to filter)
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ResultRow({ icon, title, href }: { icon: string; title: string; href: string }) {
  return (
    <a
      href={href}
      className="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-bg-subtle text-sm cursor-pointer"
    >
      <span>{icon}</span>
      <span className="flex-1">{title}</span>
      <span className="text-text-tertiary text-xs">↵</span>
    </a>
  );
}
