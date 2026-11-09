"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { setSession } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch("/api/v1/admin/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: username.trim(), password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ detail: "Authentication failed" }));
        setError(data.detail || "Invalid credentials");
        setLoading(false);
        return;
      }

      const data = await res.json();
      setSession(data.access_token, data.role || "admin", username.trim());
      router.replace("/admin");
    } catch {
      setError("Cannot reach authentication server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f3f3f3] p-4">
      <div className="w-full max-w-sm">
        {/* Header with University Logo */}
        <div className="text-center mb-6">
          <img
            src="/assets/suk-logo-color.webp"
            alt="Shivaji University, Kolhapur"
            className="w-20 h-20 mx-auto mb-3 rounded-full shadow-sm"
          />
          <h1 className="text-lg font-semibold text-[#1a1a1a]">HydroCast Operations Console</h1>
          <p className="text-xs text-[#5c5c5c] mt-1 leading-relaxed">
            Panchganga Basin Flood Forecasting System
          </p>
          <p className="text-[10px] text-[#8a8886] mt-0.5">
            Centre for Climate Change &amp; Sustainability Studies
          </p>
          <p className="text-[10px] text-[#8a8886]">
            Shivaji University, Kolhapur
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-lg border border-[#d1d1d1] shadow-sm p-6">
          <h2 className="text-sm font-semibold text-[#1a1a1a] mb-4">Administrator Sign In</h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-xs font-medium text-[#5c5c5c] mb-1">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#d1d1d1] rounded focus:outline-none focus:border-[#0078d4] focus:ring-1 focus:ring-[#0078d4] bg-white"
                placeholder="admin"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-[#5c5c5c] mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#d1d1d1] rounded focus:outline-none focus:border-[#0078d4] focus:ring-1 focus:ring-[#0078d4] bg-white"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 p-2.5 text-xs bg-[#fde7e9] border border-[#d13438] rounded text-[#a4262c]">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 mt-0.5">
                  <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full py-2 px-4 text-sm font-medium text-white bg-[#0078d4] rounded hover:bg-[#106ebe] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Authenticating..." : "Sign In"}
            </button>
          </form>

          <div className="mt-4 pt-3 border-t border-[#edebe9] space-y-2">
            <div className="text-center">
              <a href="/login/forgot" className="text-xs text-[#0078d4] hover:underline">
                Forgot password?
              </a>
            </div>
            <div className="flex items-center justify-center gap-2 text-[10px] text-[#605e5c]">
              <span className="px-1.5 py-0.5 bg-[#f3f2f1] rounded font-mono">gov.in</span>
              <span className="px-1.5 py-0.5 bg-[#f3f2f1] rounded font-mono">unishivaji.ac.in</span>
            </div>
            <p className="text-[10px] text-[#8a8886] leading-relaxed text-center">
              Authorized personnel only. All access is logged and monitored.
              Unauthorized access is prohibited under IT Act 2000, Section 66.
            </p>
          </div>
        </div>

        {/* Footer */}
        <p className="text-center text-[10px] text-[#8a8886] mt-4">
          CCCSS &middot; Shivaji University, Kolhapur
        </p>
      </div>
    </div>
  );
}
