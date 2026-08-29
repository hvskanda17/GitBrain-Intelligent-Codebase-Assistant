import type { Metadata } from "next";

import { AuthShowcase } from "@/components/auth/auth-showcase";
import { RegisterForm } from "@/components/auth/register-form";

export const metadata: Metadata = { title: "Create account · GitBrain" };

export default function RegisterPage() {
  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <div className="flex flex-col justify-center px-8 py-16 md:px-16">
        <div className="mx-auto w-full max-w-sm">
          <h1 className="font-display text-2xl font-semibold tracking-tight">Create your account</h1>
          <p className="mt-1 text-sm text-ink-soft">Start mapping a repository in a couple of minutes.</p>
          <div className="mt-8">
            <RegisterForm />
          </div>
        </div>
      </div>
      <AuthShowcase />
    </div>
  );
}
