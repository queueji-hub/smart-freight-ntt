"use client";
import { CommandBar } from "./CommandBar";
import { Bell, User } from "lucide-react";

export function Topbar({ title }: { title?: string }) {
  return (
    <header className="h-14 border-b border-border bg-bg flex items-center px-6 gap-4 sticky top-0 z-10 backdrop-blur-md">
      {title && <h1 className="font-semibold tracking-tight">{title}</h1>}
      <div className="flex-1" />
      <CommandBar />
      <button className="p-1.5 rounded-md hover:bg-bg-subtle text-text-secondary">
        <Bell size={16} />
      </button>
      <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-xs font-medium">
        <User size={14} />
      </div>
    </header>
  );
}
