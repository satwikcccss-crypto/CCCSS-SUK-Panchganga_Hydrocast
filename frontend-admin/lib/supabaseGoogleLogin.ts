import { supabase } from "./supabase";

export async function signInWithGoogleAndCheck(): Promise<{ ok: boolean; error?: string }> {
  if (!supabase) {
    return {
      ok: false,
      error: "Supabase is not configured. Please ensure NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY are set.",
    };
  }

  // 1️⃣ Start the Google popup / redirect
  const { error: authError } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: typeof window !== "undefined" ? `${window.location.origin}/auth/callback` : undefined,
    },
  });

  if (authError) {
    return { ok: false, error: authError.message };
  }

  // OAuth redirects to /auth/callback where token & email are verified
  return { ok: true };
}

