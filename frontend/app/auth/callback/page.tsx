"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { setToken, clearToken } from "@/lib/supabaseGoogleLogin";
import { AlertCircle, Loader2 } from "lucide-react";

export default function AuthCallbackPage() {
  const router = useRouter();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function handleAuth() {
      try {
        // Local JWT auth: the backend issues a JWT at /api/v1/admin/auth/token.
        // This callback page handles any redirect-back from the login flow.
        const params = new URLSearchParams(window.location.search);
        const token = params.get("token");
        const error = params.get("error");

        if (error) {
          setErrorMsg("Authentication failed: " + decodeURIComponent(error));
          setLoading(false);
          return;
        }

        if (token) {
          await setToken(token);
          router.push("/admin");
        } else {
          // No token — redirect to login page
          router.push("/login");
        }
      } catch (err: any) {
        setErrorMsg(err.message || "Authentication error occurred.");
        setLoading(false);
      }
    }

    handleAuth();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-slate-100">
        <div className="max-w-md w-full bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-2xl text-center space-y-6">
          <div className="flex justify-center">
            <div className="p-4 bg-sky-500/10 border border-sky-500/30 rounded-2xl">
              <Loader2 className="w-10 h-10 text-sky-400 animate-spin" />
            </div>
          </div>
          <p className="text-xs text-slate-400">Authenticating with HydroCast Operations Control...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4 text-slate-100">
      <div className="max-w-md w-full bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-2xl text-center space-y-6">
        <div className="flex justify-center">
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl">
            <AlertCircle className="w-10 h-10 text-rose-400" />
          </div>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-center gap-2 text-rose-400">
            <AlertCircle className="w-6 h-6 shrink-0" />
            <h2 className="text-lg font-bold">Authentication Required</h2>
          </div>
          <p className="text-sm text-slate-300 bg-rose-500/10 border border-rose-500/30 p-4 rounded-xl leading-relaxed">
            {errorMsg || "Please log in with your authorized SUK credentials to access the Operator Console."}
          </p>
          <button
            onClick={() => router.push("/login")}
            className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-white font-medium rounded-xl transition"
          >
            Return to Login
          </button>
        </div>
      </div>
    </div>
  );
}
