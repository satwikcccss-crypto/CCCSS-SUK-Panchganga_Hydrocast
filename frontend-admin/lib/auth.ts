/**
 * Lightweight JWT auth helpers for admin console.
 * Token stored in sessionStorage (cleared on tab close).
 */

const TOKEN_KEY = "hydrocast_admin_token";
const USER_KEY = "hydrocast_admin_user";

export interface AdminSession {
  token: string;
  role: string;
  username: string;
  expiresAt: number; // unix ms
}

export function getSession(): AdminSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(TOKEN_KEY);
    if (!raw) return null;
    const session: AdminSession = JSON.parse(raw);
    if (Date.now() > session.expiresAt) {
      clearSession();
      return null;
    }
    return session;
  } catch {
    return null;
  }
}

export function setSession(token: string, role: string, username: string): void {
  const payload = parseJwt(token);
  const expiresAt = payload?.exp ? payload.exp * 1000 : Date.now() + 24 * 60 * 60 * 1000;
  const session: AdminSession = { token, role, username, expiresAt };
  sessionStorage.setItem(TOKEN_KEY, JSON.stringify(session));
  sessionStorage.setItem(USER_KEY, username);
}

export function clearSession(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function getToken(): string | null {
  return getSession()?.token ?? null;
}

/**
 * Roles:
 *  - "admin"  → operator (full control incl. DB, trigger, dispatch, services)
 *  - "viewer" → official/university read-only (dashboard + export only)
 * Anything not "admin" is treated as viewer (fail closed).
 */
const OPERATOR_ROLES = new Set(["admin"]);

export function isOperator(): boolean {
  if (typeof window === "undefined") return false;
  const session = getSession();
  if (!session) return false; // fail closed: no session => no admin actions
  return OPERATOR_ROLES.has(session.role);
}

export function isViewer(): boolean {
  const session = getSession();
  return session !== null && !OPERATOR_ROLES.has(session.role);
}

function parseJwt(token: string): Record<string, any> | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(json);
  } catch {
    return null;
  }
}
