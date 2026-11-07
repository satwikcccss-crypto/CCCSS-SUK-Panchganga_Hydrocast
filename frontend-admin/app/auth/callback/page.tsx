"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import { Cpu, AlertCircle, Loader2 } from "lucide-react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function handleAuth() {
      if (!supabase) {
        setErrorMsg("Supabase client is not configured. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.");
        return;
      }

      try {
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        if (sessionError || !session?.user) {
          setErrorMsg(sessionError?.message || "Failed to retrieve authenticated session from Google.");
          return;
        }

        const email = session.user.email || "";

        // Verify with backend Google check
        const res = await fetch("/api/v1/admin/auth/google", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, access_token: session.access_token }),
        });

        const data = await res.json().catch(() => ({}));

        if (!res.ok || !data.ok) {
          await supabase.auth.signOut();
          setErrorMsg(
            data.detail ||
            "Unauthorized. Only the four approved email accounts may access HydroCast Operations Control. Please contact satwikcccss@gmail.com for access."
          );
          return;
        }

        // Store tokens
        localStorage.setItem("admin_token", data.access_token);
        localStorage.setItem("admin_role", data.role || "dev");
        localStorage.setItem("admin_user", email);
        document.cookie = `admin_token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`;

        router.push("/admin");
      } catch (err: any) {
        setErrorMsg(err.message || "Authentication error occurred.");
      }
    }

    handleAuth();
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-slate-100">
      <div className="max-w-md w-full bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-2xl text-center space-y-6">
        <div className="flex justify-center">
          <div className="p-4 bg-sky-500/10 border border-sky-500/30 rounded-2xl">
            <Cpu className="w-10 h-10 text-sky-400" />
          </div>
        </div>

        {errorMsg ? (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-2 text-rose-400">
              <AlertCircle className="w-6 h-6 shrink-0" />
              <h2 className="text-lg font-bold">Access Denied</h2>
            </div>
            <p className="text-sm text-slate-300 bg-rose-500/10 border border-rose-500/30 p-4 rounded-xl leading-relaxed">
              {errorMsg}
            </p>
            <button
              onClick={() => router.push("/login")}
              className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition"
            >
              Return to Login
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-center gap-2 text-sky-400">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span className="text-base font-semibold">Verifying Google Credentials...</span>
            </div>
            <p className="text-xs text-slate-400">
              Validating authorized account against HydroCast Operations Control access policy.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

