"use client";
import { Home, Package, Sparkles, Users, FileText, BarChart3, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const navItems = [
  { href: "/", icon: Home, label: "Dashboard" },
  { href: "/shipments", icon: Package, label: "Shipments" },
  { href: "/ai", icon: Sparkles, label: "AI Parser" },
  { href: "/customers", icon: Users, label: "Customers", disabled: true },
  { href: "/quotes", icon: FileText, label: "Quotes", disabled: true },
  { href: "/analytics", icon: BarChart3, label: "Analytics", disabled: true },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 border-r border-border bg-bg-elevated flex flex-col h-screen sticky top-0">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md bg-accent flex items-center justify-center text-white font-bold text-sm">
            F
          </div>
          <span className="font-semibold tracking-tight">Freight OS</span>
        </div>
      </div>

      <nav className="flex-1 p-2 space-y-0.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.disabled ? "#" : item.href}
              className={clsx(
                "flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-sm transition-colors",
                active && "bg-accent-subtle text-text-primary",
                !active && !item.disabled && "text-text-secondary hover:text-text-primary hover:bg-bg-subtle",
                item.disabled && "text-text-tertiary cursor-not-allowed opacity-60"
              )}
            >
              <Icon size={15} strokeWidth={2} />
              <span>{item.label}</span>
              {item.disabled && (
                <span className="ml-auto text-[10px] text-text-tertiary">Soon</span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="p-2 border-t border-border">
        <div className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-sm text-text-secondary hover:bg-bg-subtle cursor-pointer">
          <Settings size={15} />
          <span>Settings</span>
        </div>
      </div>
    </aside>
  );
}
