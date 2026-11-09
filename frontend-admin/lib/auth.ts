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
 *  - "govt"  → read-only viewer (gov.in / unishivaji.ac.in officials)
 *  - "dev"   → operator (researchers with trigger/DB/log access)
 *  - "admin" → superadmin (full control including user management)
 */
const OPERATOR_ROLES = new Set(["dev", "admin"]);

export function isOperator(): boolean {
  const session = getSession();
  return session !== null && OPERATOR_ROLES.has(session.role);
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
