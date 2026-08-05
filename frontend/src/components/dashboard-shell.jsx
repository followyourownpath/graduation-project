"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FileText, LayoutDashboard, Loader2, LogOut, Menu, ShieldAlert, ShieldCheck, X } from "lucide-react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Applications", href: "/applications", icon: FileText },
  { name: "Rules engine", href: "/rules-engine", icon: ShieldAlert },
];

export function initials(name = "Staff") {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function Brand() {
  return <Link href="/dashboard" className="flex items-center gap-2.5 text-white"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/15 text-blue-300"><ShieldCheck className="h-5 w-5" /></span><span className="text-base font-semibold tracking-tight">SmartFINN</span></Link>;
}

function Navigation({ pathname, onNavigate }) {
  return <nav className="space-y-1.5" aria-label="Main navigation">{navItems.map(({ name, href, icon: Icon }) => {
    const active = pathname === href || pathname.startsWith(`${href}/`);
    return <Link key={href} href={href} onClick={onNavigate} className={cn("flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition-colors", active ? "bg-blue-600 text-white shadow-sm" : "text-slate-400 hover:bg-slate-900 hover:text-white")}><Icon className="h-4 w-4" />{name}</Link>;
  })}</nav>;
}

function UserAvatar({ staff }) {
  return <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">{staff ? initials(staff.full_name) : "…"}</div>;
}

export function DashboardShell({ children }) {
  const pathname = usePathname();
  const router = useRouter();
  const [staff, setStaff] = useState(null);
  const [signingOut, setSigningOut] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    let active = true;
    api.getCurrentStaff().then((identity) => { if (active) setStaff(identity.staff_profile); }).catch(async () => {
      if (!active) return;
      await createClient().auth.signOut();
      router.replace("/login");
      router.refresh();
    });
    return () => { active = false; };
  }, [router]);

  async function handleSignOut() {
    setSigningOut(true);
    await createClient().auth.signOut();
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="flex min-h-dvh bg-slate-50">
      <aside className="sticky top-0 hidden h-dvh w-60 shrink-0 flex-col border-r border-slate-800 bg-slate-950 text-white lg:flex">
        <div className="flex h-16 items-center border-b border-slate-800 px-5"><Brand /></div>
        <div className="flex-1 px-3 py-5"><Navigation pathname={pathname} /></div>
        <div className="border-t border-slate-800 p-3">
          <div className="mb-3 flex items-center gap-2 px-2"><UserAvatar staff={staff} /><div className="min-w-0"><p className="truncate text-sm font-medium text-white">{staff?.full_name || "Loading profile"}</p><p className="text-xs capitalize text-slate-500">{staff?.role || "Staff"}</p></div></div>
          <Button type="button" variant="ghost" onClick={handleSignOut} disabled={signingOut} className="w-full justify-start text-slate-400 hover:bg-slate-900 hover:text-white"><LogOut className="mr-2 h-4 w-4" />{signingOut ? "Signing out…" : "Sign out"}</Button>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur sm:px-6 lg:px-8">
          <div className="flex items-center gap-3"><Button type="button" variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu className="h-5 w-5" /></Button><Link href="/dashboard" className="flex items-center gap-2 text-slate-950 lg:hidden"><ShieldCheck className="h-5 w-5 text-blue-600" /><span className="font-semibold tracking-tight">SmartFINN</span></Link><p className="hidden text-sm font-medium text-slate-500 lg:block">Mortgage compliance workspace</p></div>
          <div className="flex items-center gap-2"><div className="hidden text-right sm:block"><p className="text-sm font-medium text-slate-700">{staff?.full_name || "Loading profile"}</p><p className="text-xs capitalize text-slate-500">{staff?.role || "Staff"}</p></div><UserAvatar staff={staff} /></div>
        </header>
        <main className="min-w-0">{children}</main>
      </div>

      <Dialog open={mobileOpen} onOpenChange={setMobileOpen}>
        <DialogContent showCloseButton={false} className="fixed top-0 left-0 h-dvh w-[min(20rem,88vw)] max-w-none translate-x-0 translate-y-0 rounded-none border-0 bg-slate-950 p-0 text-white shadow-2xl sm:max-w-none">
          <DialogTitle className="sr-only">Navigation</DialogTitle><DialogDescription className="sr-only">Navigate SmartFINN</DialogDescription>
          <div className="flex h-16 items-center justify-between border-b border-slate-800 px-5"><Brand /><Button type="button" variant="ghost" size="icon" aria-label="Close navigation" className="text-slate-300 hover:bg-slate-900 hover:text-white" onClick={() => setMobileOpen(false)}><X className="h-5 w-5" /></Button></div>
          <div className="px-3 py-5"><Navigation pathname={pathname} onNavigate={() => setMobileOpen(false)} /></div>
          <div className="absolute right-0 bottom-0 left-0 border-t border-slate-800 p-4"><Button type="button" variant="ghost" onClick={handleSignOut} disabled={signingOut} className="w-full justify-start text-slate-400 hover:bg-slate-900 hover:text-white"><LogOut className="mr-2 h-4 w-4" />{signingOut ? "Signing out…" : "Sign out"}</Button></div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
