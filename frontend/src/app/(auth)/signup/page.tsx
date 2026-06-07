"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Eye, EyeOff, Shield, ShieldCheck, Lock, Sparkles } from "lucide-react";
import { signup } from "@/services/api";

export default function SignupPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await signup({
        fullName: String(form.get("fullName")),
        email: String(form.get("email")),
        password: String(form.get("password")),
      });
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.message || "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen flex-col md:flex-row overflow-hidden">
      {/* ── LEFT: Branding Panel ── */}
      <div className="relative flex flex-1 flex-col justify-between overflow-hidden bg-gradient-to-br from-navy to-navy-light p-6 md:p-16 min-h-[360px] md:min-h-screen">
        {/* Ambient glow */}
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background:
              "radial-gradient(circle at 50% 50%, rgba(201, 168, 76, 0.05) 0%, transparent 50%)",
          }}
        />

        {/* Logo */}
        <div className="relative z-10 flex items-center gap-2">
          <Shield className="h-8 w-8 text-gold-light" />
          <h1 className="font-heading text-2xl font-bold text-white tracking-tight">InsuraMind</h1>
        </div>

        {/* Center graphic */}
        <div className="relative z-10 flex flex-col items-center text-center my-8">
          <div className="relative flex h-64 w-full max-w-md items-center justify-center">
            <div className="absolute h-64 w-48 rotate-[-6deg] rounded-xl glass-panel shadow-[0_4px_30px_rgba(201,168,76,0.1)] border border-gold-light/30 transition-transform duration-500 hover:rotate-0" />
            <div className="absolute h-64 w-48 rotate-[6deg] rounded-xl glass-panel shadow-[0_4px_30px_rgba(0,109,66,0.1)] border border-emerald/40 flex items-center justify-center transition-transform duration-500 hover:rotate-0">
              <Sparkles className="h-10 w-10 text-gold-light animate-pulse" />
            </div>
            <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
              <path d="M10,50 Q50,10 90,50" fill="none" stroke="rgba(128, 217, 164, 0.3)" strokeWidth="1" />
              <path d="M10,80 Q50,100 90,80" fill="none" stroke="rgba(201, 168, 76, 0.2)" strokeWidth="1" />
            </svg>
          </div>
          <p className="mt-8 max-w-sm text-body-lg text-text-on-dark-muted">
            AI-powered insurance intelligence at your fingertips.
          </p>
        </div>

        {/* Trust indicators */}
        <div className="relative z-10 flex flex-wrap justify-center gap-4 text-text-on-dark-muted/80">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="h-4 w-4" />
            <span className="text-caption">Bank-grade encryption</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Lock className="h-4 w-4" />
            <span className="text-caption">IRDAI compliant</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Sparkles className="h-4 w-4" />
            <span className="text-caption">AI-verified answers</span>
          </div>
        </div>
      </div>

      {/* ── RIGHT: Signup Form ── */}
      <div className="flex flex-1 flex-col justify-center bg-white px-6 py-12 md:px-16 relative -mt-6 md:mt-0 rounded-t-3xl md:rounded-none shadow-[0_-10px_40px_rgba(0,0,0,0.1)] md:shadow-none z-20">
        <div className="mx-auto w-full max-w-sm">
          <h2 className="font-heading text-display-lg text-text-primary mb-2">Create your account</h2>
          <p className="text-body-sm text-text-muted mb-8">Upload policies and get grounded answers with citations.</p>

          <form onSubmit={onSubmit} className="space-y-5">
            {/* Full Name */}
            <div className="floating-label-input">
              <input
                id="signup-name"
                name="fullName"
                type="text"
                placeholder=" "
                required
                autoComplete="name"
              />
              <label htmlFor="signup-name">Full Name</label>
            </div>

            {/* Email */}
            <div className="floating-label-input">
              <input
                id="signup-email"
                name="email"
                type="email"
                placeholder=" "
                required
                autoComplete="email"
              />
              <label htmlFor="signup-email">Email Address</label>
            </div>

            {/* Password */}
            <div className="floating-label-input">
              <input
                id="signup-password"
                name="password"
                type={showPassword ? "text" : "password"}
                placeholder=" "
                required
                minLength={8}
                className="pr-12"
              />
              <label htmlFor="signup-password">Password</label>
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-gold transition-colors"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <Eye className="h-5 w-5" /> : <EyeOff className="h-5 w-5" />}
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-input border border-danger/20 bg-danger-surface px-3 py-2 text-sm text-danger">
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="btn-primary-gradient w-full"
            >
              {loading ? "Creating account..." : "Create account"}
            </button>

            {/* Sign in link */}
            <div className="text-center mt-4">
              <span className="text-body-sm text-text-muted">Already have an account? </span>
              <Link href="/login" className="text-label text-gold hover:underline font-medium">
                Sign in
              </Link>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="absolute bottom-4 left-0 w-full text-center">
          <p className="text-caption text-text-muted text-[11px]">© 2024 InsuraMind. All rights reserved.</p>
        </div>
      </div>
    </main>
  );
}
