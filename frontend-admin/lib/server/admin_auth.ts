/**
 * Server-side token validation against the admin backend.
 * Import only from server-side route handlers (never from client components).
 *
 * The operator console has no shared JWT secret, so the canonical check is to
 * forward the caller's bearer token to an authenticated admin endpoint and
 * treat 2xx as authorized. Use `getAdminClaims` to validate ANY valid console JWT
 * (viewer or admin) and check `role === 'admin'` for operator-only routes.
 * This prevents "presence-only" bearer checks from granting access, and
 * prevents official/viewer accounts from using operator-only endpoints.
 */
export async function getAdminClaims(req: Request): Promise<
  | { status: "authorized"; claims: { sub?: string; role?: string } }
  | { status: "unauthorized" }
  | { status: "unavailable" }
> {
  const token = bearer(req);
  if (!token) return { status: "unauthorized" };

  const origin = (
    process.env.ADMIN_BACKEND_ORIGIN ||
    process.env.ADMIN_API_ORIGIN ||
    "http://127.0.0.1:8001"
  ).replace(/\/+$/, "");

  try {
    const res = await fetch(`${origin}/api/v1/admin/me`, {
      headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    if (res.ok) {
      const claims = await res.json().catch(() => ({}));
      return { status: "authorized", claims };
    }
    if (res.status === 401 || res.status === 403) return { status: "unauthorized" };
    return { status: "unavailable" };
  } catch {
    return { status: "unavailable" };
  }
}

export function isAdminUnlocked(claims: { role?: string }): boolean {
  return claims.role === "admin";
}

export function bearer(req: Request): string | null {
  const h = req.headers.get("authorization") || "";
  return h.toLowerCase().startsWith("bearer ") ? h.slice(7).trim() || null : null;
}
