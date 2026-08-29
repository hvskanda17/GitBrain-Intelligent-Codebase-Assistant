import type { Metadata } from "next";

import { AuthShowcase } from "@/components/auth/auth-showcase";
import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = { title: "Sign in · GitBrain" };

export default function LoginPage() {
  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <div className="flex flex-col justify-center px-8 py-16 md:px-16">
        <div className="mx-auto w-full max-w-sm">
          <h1 className="font-display text-2xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-1 text-sm text-ink-soft">Sign in to keep working with your repositories.</p>
          <div className="mt-8">
            <LoginForm />
          </div>
        </div>
      </div>
      <AuthShowcase />
    </div>
  );
}
