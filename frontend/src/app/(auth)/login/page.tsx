"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { login } from "@/services/api";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await login({
        email: String(form.get("email")),
        password: String(form.get("password"))
      });
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err?.response?.data?.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-panel px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <h1 className="text-xl font-semibold">InsuraMind</h1>
          <p className="text-sm text-muted">Sign in to your insurance intelligence workspace.</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <Input name="email" type="text" placeholder="Email or username" autoComplete="username" required />
            <Input name="password" type="password" placeholder="Password" required />
            {error && <p className="text-sm text-risk">{error}</p>}
            <Button className="w-full" disabled={loading}>{loading ? "Signing in..." : "Sign in"}</Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted">
            New here? <Link className="font-medium text-brand" href="/signup">Create account</Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
