// frontend/lib/supabase.ts
// Supabase (cloud) has been removed from this on-premises Windows Server deployment.
// All data now comes from the local FastAPI backend (Port 8000) which queries
// PostgreSQL 16 directly. This module is kept as a compatibility shim that
// always returns null so existing imports don't break.

export const supabase = null;

export async function supabaseAuth() {
  // Local auth is handled by backend JWT via /api/v1/admin/auth/token
  return { data: null, error: { message: "Use backend JWT auth instead" } };
}

export async function supabaseSignOut() {
  return { error: null };
}
