// frontend/lib/supabaseGoogleLogin.ts
// Google OAuth via Supabase has been removed. Local auth uses backend JWT
// (POST /api/v1/admin/auth/token with bcrypt-verified credentials).

export async function googleLogin() {
  // Redirect to backend admin login instead of Supabase OAuth
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
  return { data: null, error: { message: "Use local admin login" } };
}

export async function isAuthenticated(): Promise<boolean> {
  // Check for a valid JWT in localStorage
  if (typeof window === "undefined") return false;
  const token = localStorage.getItem("hydrocast_jwt");
  return !!token;
}

export async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("hydrocast_jwt");
}

export async function setToken(token: string) {
  if (typeof window !== "undefined") {
    localStorage.setItem("hydrocast_jwt", token);
  }
}

export async function clearToken() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("hydrocast_jwt");
  }
}
