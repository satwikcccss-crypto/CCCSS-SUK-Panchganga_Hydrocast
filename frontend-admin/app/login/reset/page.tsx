"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    if (newPassword.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/v1/admin/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          reset_code: code.trim(),
          new_password: newPassword,
        }),
      });

      const data = await res.json().catch(() => ({ detail: "Request failed" }));

      if (!res.ok) {
        setError(data.detail || "Reset failed. Check your code and try again.");
        setLoading(false);
        return;
      }

      setSuccess(true);
    } catch {
      setError("Cannot reach server. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f3f3f3] p-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-6">
            <img
              src="/assets/suk-logo-color.webp"
              alt="Shivaji University, Kolhapur"
              className="w-16 h-16 mx-auto mb-3 rounded-full shadow-sm"
            />
          </div>
          <div className="bg-white rounded-lg border border-[#d1d1d1] shadow-sm p-6 text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[#dff6dd] flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#107c10" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <h2 className="text-base font-semibold text-[#1a1a1a] mb-2">Password Updated</h2>
            <p className="text-xs text-[#605e5c] mb-4">
              Your password has been reset. You can now sign in with your new password.
            </p>
            <button
              onClick={() => router.push("/login")}
              className="w-full py-2 px-4 text-sm font-medium text-white bg-[#0078d4] rounded hover:bg-[#106ebe] transition-colors"
            >
              Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f3f3f3] p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <img
            src="/assets/suk-logo-color.webp"
            alt="Shivaji University, Kolhapur"
            className="w-16 h-16 mx-auto mb-3 rounded-full shadow-sm"
          />
          <h1 className="text-lg font-semibold text-[#1a1a1a]">Reset Password</h1>
          <p className="text-xs text-[#5c5c5c] mt-1">Enter the 6-digit code from your administrator</p>
        </div>

        <div className="bg-white rounded-lg border border-[#d1d1d1] shadow-sm p-6">
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
              />
            </div>

            <div>
              <label htmlFor="code" className="block text-xs font-medium text-[#5c5c5c] mb-1">
                Reset Code
              </label>
              <input
                id="code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                required
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                className="w-full px-3 py-2 text-sm border border-[#d1d1d1] rounded focus:outline-none focus:border-[#0078d4] focus:ring-1 focus:ring-[#0078d4] bg-white text-center tracking-[0.5em] font-mono text-lg"
                placeholder="000000"
              />
            </div>

            <div>
              <label htmlFor="new-password" className="block text-xs font-medium text-[#5c5c5c] mb-1">
                New Password
              </label>
              <input
                id="new-password"
                type="password"
                autoComplete="new-password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#d1d1d1] rounded focus:outline-none focus:border-[#0078d4] focus:ring-1 focus:ring-[#0078d4] bg-white"
                placeholder="Minimum 8 characters"
              />
            </div>

            <div>
              <label htmlFor="confirm-password" className="block text-xs font-medium text-[#5c5c5c] mb-1">
                Confirm Password
              </label>
              <input
                id="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-[#d1d1d1] rounded focus:outline-none focus:border-[#0078d4] focus:ring-1 focus:ring-[#0078d4] bg-white"
                placeholder="Re-enter new password"
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
              disabled={loading || !username || code.length !== 6 || !newPassword || !confirmPassword}
              className="w-full py-2 px-4 text-sm font-medium text-white bg-[#0078d4] rounded hover:bg-[#106ebe] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Resetting..." : "Reset Password"}
            </button>
          </form>

          <div className="mt-4 pt-3 border-t border-[#edebe9]">
            <div className="flex gap-2 text-xs">
              <Link href="/login/forgot" className="text-[#0078d4] hover:underline">
                Need a code?
              </Link>
              <span className="text-[#d1d1d1]">|</span>
              <Link href="/login" className="text-[#0078d4] hover:underline">
                Back to Sign In
              </Link>
            </div>
          </div>
        </div>

        <p className="text-center text-[10px] text-[#8a8886] mt-4">
          CCCSS &middot; Shivaji University, Kolhapur
        </p>
      </div>
    </div>
  );
}
