import type { ReactNode } from "react";

import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { requireSession } from "@/lib/api";

export default async function ProjectsLayout({ children }: { children: ReactNode }) {
  const user = await requireSession();

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Header user={user} />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
