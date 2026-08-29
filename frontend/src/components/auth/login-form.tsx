"use client";

import { useActionState } from "react";
import Link from "next/link";

import { loginAction } from "@/actions/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginForm() {
  const [state, formAction, isPending] = useActionState(loginAction, {});

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">Email</Label>
        <Input id="email" name="email" type="email" autoComplete="email" required />
      </div>
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">Password</Label>
        <Input id="password" name="password" type="password" autoComplete="current-password" required />
      </div>
      {state.error && <p className="text-sm text-danger">{state.error}</p>}
      <Button type="submit" disabled={isPending} className="mt-2">
        {isPending ? "Signing in…" : "Sign in"}
      </Button>
      <p className="text-center text-sm text-ink-soft">
        No account?{" "}
        <Link href="/register" className="text-accent hover:underline">
          Create one
        </Link>
      </p>
    </form>
  );
}
