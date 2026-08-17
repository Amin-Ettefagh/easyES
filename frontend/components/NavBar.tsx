"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getActiveOrganization, getUser, clearSession, isAuthenticated, setActiveOrganization } from "@/lib/auth";
import type { User } from "@/lib/types";
import Icon, { type IconName } from "@/components/Icon";
import ThemeToggle from "@/components/ThemeToggle";

const LINKS = [
  { href: "/dashboard", label: "Overview", icon: "grid" },
  { href: "/company", label: "Organization", icon: "building" },
  { href: "/agents", label: "AI workforce", icon: "agents" },
  { href: "/providers", label: "Providers & models", icon: "provider" },
  { href: "/workflow", label: "Workflows", icon: "workflow" },
];

export default function NavBar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  // Client-side auth guard: anything rendering the shell requires a token.
  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    setUser(getUser());
  }, [router, pathname]);

  function logout() {
    clearSession();
    router.replace("/login");
  }

  const selectedOrg = getActiveOrganization();
  const org = user?.organizations?.find((item) => item.uuid === selectedOrg) || user?.organizations?.[0];

  function switchOrganization(uuid: string) {
    setActiveOrganization(uuid);
    window.location.reload();
  }

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark"><Icon name="spark" /></span>
        <span className="brand-copy">easy<span>ES</span></span>
      </div>
      <label className="workspace-pill company-switcher">
        <span className="workspace-avatar">{(org?.name || "C").charAt(0).toUpperCase()}</span>
        <span><small>Company</small><select aria-label="Active company" value={org?.uuid || ""} onChange={(event) => switchOrganization(event.target.value)}>{user?.organizations?.map((item) => <option key={item.uuid} value={item.uuid}>{item.name}</option>)}</select></span>
        <span className="workspace-chevron">⌄</span>
      </label>
      <div className="nav-label">Command center</div>
      <nav aria-label="Primary navigation">
        {LINKS.map((l) => {
          const active = pathname === l.href || pathname.startsWith(`${l.href}/`);
          return (
            <Link
              key={l.href}
              href={l.href}
              className={`nav-link ${active ? "active" : ""}`}
            >
              <Icon name={l.icon as IconName} />
              <span>{l.label}</span>
              {active && <span className="nav-active-dot" />}
            </Link>
          );
        })}
      </nav>
      <ThemeToggle />
      <div className="system-card">
        <div className="system-card-head"><span className="live-dot" /> Systems operational</div>
        <div className="system-card-copy">Provider gateway & agent catalog online</div>
      </div>
      <div className="user-box">
        <span className="user-avatar">{(user?.display_name || user?.username || "A").charAt(0).toUpperCase()}</span>
        <span className="user-meta"><strong>{user?.display_name || user?.username || "…"}</strong><small>Administrator</small></span>
        <button className="icon-btn" onClick={logout} title="Log out" aria-label="Log out"><Icon name="logout" /></button>
      </div>
    </aside>
  );
}
