// Token + user storage helpers. The demo keeps JWTs in localStorage: simple and
// good enough for a single-origin dev/demo deployment. (For production you'd move
// to httpOnly cookies; noted in the frontend README.)
import type { User } from "./types";

const ACCESS_KEY = "easyes.access";
const REFRESH_KEY = "easyes.refresh";
const USER_KEY = "easyes.user";
const ORGANIZATION_KEY = "easyes.organization";

export function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getAccess(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function getRefresh(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(REFRESH_KEY);
}

export function getUser(): User | null {
  if (!isBrowser()) return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function saveSession(access: string, refresh: string, user: User): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ACCESS_KEY, access);
  window.localStorage.setItem(REFRESH_KEY, refresh);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
  const selected = window.localStorage.getItem(ORGANIZATION_KEY);
  if (!selected || !user.organizations.some((organization) => organization.uuid === selected)) {
    if (user.organizations[0]) window.localStorage.setItem(ORGANIZATION_KEY, user.organizations[0].uuid);
  }
}

export function saveUser(user: User): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getActiveOrganization(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ORGANIZATION_KEY);
}

export function setActiveOrganization(uuid: string): void {
  if (!isBrowser()) return;
  window.localStorage.setItem(ORGANIZATION_KEY, uuid);
}

export function clearSession(): void {
  if (!isBrowser()) return;
  window.localStorage.removeItem(ACCESS_KEY);
  window.localStorage.removeItem(REFRESH_KEY);
  window.localStorage.removeItem(USER_KEY);
  window.localStorage.removeItem(ORGANIZATION_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccess();
}
