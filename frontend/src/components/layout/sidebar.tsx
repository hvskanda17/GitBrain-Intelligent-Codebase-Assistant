import Link from "next/link";

export function Sidebar() {
  return (
    <aside className="hidden w-56 shrink-0 border-r border-[#2E2F35] bg-[#1A1B1E] text-[#FAF8F4] md:flex md:flex-col">
      <div className="border-b border-white/10 px-5 py-5">
        <Link href="/projects" className="font-display text-lg font-semibold tracking-tight">
          GitBrain
        </Link>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        <Link
          href="/projects"
          className="rounded-md px-3 py-2 text-sm text-[#FAF8F4]/80 transition-colors hover:bg-white/5 hover:text-[#FAF8F4]"
        >
          Projects
        </Link>
      </nav>
      <div className="border-t border-white/10 p-3 font-mono text-[11px] text-[#FAF8F4]/40">
        Phase 3 · frontend
      </div>
    </aside>
  );
}
