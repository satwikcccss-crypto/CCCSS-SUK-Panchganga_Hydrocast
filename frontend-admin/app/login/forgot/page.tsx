"use client";

import Link from "next/link";

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f3f3f3] p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <img
            src="/assets/suk-logo-color.webp"
            alt="Shivaji University, Kolhapur"
            className="w-16 h-16 mx-auto mb-3 rounded-full shadow-sm"
          />
          <h1 className="text-lg font-semibold text-[#1a1a1a]">Password Reset</h1>
          <p className="text-xs text-[#5c5c5c] mt-1">HydroCast Operations Console</p>
        </div>

        <div className="bg-white rounded-lg border border-[#d1d1d1] shadow-sm p-6">
          <div className="flex items-start gap-3 p-3 mb-4 bg-[#f0f6ff] border border-[#cce0ff] rounded text-[#0050a0]">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="shrink-0 mt-0.5">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            <div className="text-xs leading-relaxed">
              <p className="font-semibold mb-1">Contact Your System Administrator</p>
              <p>
                For security, password resets are handled by the system administrator.
                They will provide you with a <strong>6-digit reset code</strong> valid for 1 hour.
              </p>
            </div>
          </div>

          <div className="space-y-3 text-xs text-[#605e5c]">
            <div className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-[#0078d4] text-white flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">1</span>
              <p>Contact the CCCSS system administrator and request a password reset for your account.</p>
            </div>
            <div className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-[#0078d4] text-white flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">2</span>
              <p>The administrator will generate a 6-digit reset code and share it with you.</p>
            </div>
            <div className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-[#0078d4] text-white flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">3</span>
              <p>Use the code on the reset page to set your new password.</p>
            </div>
          </div>

          <div className="mt-5 flex flex-col gap-2">
            <Link
              href="/login/reset"
              className="w-full py-2 px-4 text-sm font-medium text-white bg-[#0078d4] rounded hover:bg-[#106ebe] text-center transition-colors"
            >
              I Have a Reset Code
            </Link>
            <Link
              href="/login"
              className="w-full py-2 px-4 text-sm font-medium text-[#0078d4] bg-white border border-[#d1d1d1] rounded hover:bg-[#f3f2f1] text-center transition-colors"
            >
              Back to Sign In
            </Link>
          </div>
        </div>

        <p className="text-center text-[10px] text-[#8a8886] mt-4">
          CCCSS &middot; Shivaji University, Kolhapur
        </p>
      </div>
    </div>
  );
}
