"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FileText, LayoutDashboard, Loader2, LogOut, Settings, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";
import { withBasePath } from "@/lib/auth-utils";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Applications", href: "/applications", icon: FileText },
  { name: "Settings", href: "#", icon: Settings },
];

export function initials(name = "Staff") {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

export function DashboardShell({ children }) {
  const pathname = usePathname();
  const router = useRouter();
  const [staff, setStaff] = useState(null);
  const [profileError, setProfileError] = useState("");
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    let active = true;
    api.getCurrentStaff().then((identity) => {
      if (active) setStaff(identity.staff_profile);
    }).catch(async (error) => {
      if (!active) return;
      setProfileError(error.message);
      await createClient().auth.signOut();
      router.replace(withBasePath("/login"));
      router.refresh();
    });
    return () => { active = false; };
  }, [router]);

  async function handleSignOut() {
    setSigningOut(true);
    await createClient().auth.signOut();
    router.replace(withBasePath("/login"));
    router.refresh();
  }

  return (
    <div className="flex h-screen bg-slate-50">
      <aside className="flex w-64 flex-col bg-slate-900 text-white">
        <div className="flex h-16 items-center border-b border-slate-800 px-6">
          <ShieldCheck className="mr-2 h-6 w-6 text-blue-400" />
          <span className="text-lg font-bold tracking-tight">SmartFinn</span>
        </div>
        <nav className="flex-1 space-y-2 px-4 py-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            return <Link key={item.name} href={item.href} className={cn(
              "flex items-center rounded-lg px-4 py-3 text-sm font-medium transition-colors",
              pathname === item.href ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white",
            )}><Icon className="mr-3 h-5 w-5" />{item.name}</Link>;
          })}
        </nav>
        <div className="border-t border-slate-800 p-4">
          <button type="button" onClick={handleSignOut} disabled={signingOut} className="flex w-full items-center rounded-lg px-4 py-3 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-60">
            {signingOut ? <Loader2 className="mr-3 h-5 w-5 animate-spin" /> : <LogOut className="mr-3 h-5 w-5" />}
            {signingOut ? "Signing out…" : "Sign out"}
          </button>
        </div>
      </aside>
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-8">
          <h1 className="text-xl font-semibold text-slate-800">{pathname.includes("application") ? "Review Application" : "Overview"}</h1>
          <div className="flex items-center gap-2" aria-live="polite">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-700">{staff ? initials(staff.full_name) : "…"}</div>
            <div className="text-right">
              <p className="text-sm font-medium text-slate-700">{profileError || staff?.full_name || "Loading staff profile"}</p>
              {staff?.role && <p className="text-xs capitalize text-slate-400">{staff.role}</p>}
            </div>
          </div>
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
