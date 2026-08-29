import { LogOut } from "lucide-react";

import { logoutAction } from "@/actions/auth";
import type { UserProfile } from "@/types/api";

export function Header({ user }: { user: UserProfile }) {
  return (
    <header className="flex items-center justify-between border-b border-line px-6 py-4">
      <div className="font-mono text-xs text-ink-soft">
        {user.full_name ?? user.email} · <span className="uppercase">{user.role}</span>
      </div>
      <form action={logoutAction}>
        <button
          type="submit"
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-ink-soft transition-colors hover:bg-muted hover:text-ink"
        >
          <LogOut className="size-3.5" />
          Sign out
        </button>
      </form>
    </header>
  );
}
