import type { ReactNode, SVGProps } from "react";

export type IconName =
  | "grid" | "building" | "agents" | "workflow" | "spark" | "project"
  | "activity" | "roles" | "arrow" | "logout" | "check" | "shield"
  | "pulse" | "command" | "provider";

const paths: Record<IconName, ReactNode> = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></>,
  building: <><path d="M4 21V5a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v16"/><path d="M9 21v-4h3v4M8 7h1m3 0h1M8 11h1m3 0h1M17 9h2a1 1 0 0 1 1 1v11M2 21h20"/></>,
  agents: <><circle cx="12" cy="8" r="4"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0M5 9H3m18 0h-2M12 2V1"/></>,
  workflow: <><rect x="3" y="3" width="6" height="5" rx="1.5"/><rect x="15" y="16" width="6" height="5" rx="1.5"/><rect x="3" y="16" width="6" height="5" rx="1.5"/><path d="M6 8v8m3-10h4a5 5 0 0 1 5 5v5"/></>,
  spark: <path d="m12 2 1.55 5.45L19 9l-5.45 1.55L12 16l-1.55-5.45L5 9l5.45-1.55L12 2Zm7 13 .75 2.25L22 18l-2.25.75L19 21l-.75-2.25L16 18l2.25-.75L19 15Z"/>,
  project: <><path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H10l2 2h6.5A2.5 2.5 0 0 1 21 9.5v8a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5v-10Z"/><path d="M8 13h8m-4-4v8"/></>,
  activity: <path d="M3 12h4l2.2-6 4.2 12 2.2-6H21"/>,
  roles: <><circle cx="9" cy="8" r="3"/><circle cx="17" cy="10" r="2.5"/><path d="M3 20a6 6 0 0 1 12 0m0-5a5 5 0 0 1 6 5"/></>,
  arrow: <><path d="M5 12h14M14 7l5 5-5 5"/></>,
  logout: <><path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5M14 8l4 4-4 4m4-4H8"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  shield: <><path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10Z"/><path d="m9 12 2 2 4-5"/></>,
  pulse: <><path d="M3 12h4l2-5 4 10 2-5h6"/><circle cx="12" cy="12" r="10"/></>,
  command: <><rect x="3" y="3" width="18" height="18" rx="5"/><path d="m8 9 3 3-3 3m5 0h3"/></>,
  provider: <><path d="M8 3v4m8-4v4M5 8h14v3a7 7 0 0 1-7 7 7 7 0 0 1-7-7V8Z"/><path d="M12 18v3m-3 0h6"/></>,
};

export default function Icon({ name, ...props }: SVGProps<SVGSVGElement> & { name: IconName }) {
  return <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>;
}
